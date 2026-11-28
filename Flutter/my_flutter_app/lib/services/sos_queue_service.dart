import 'dart:async';
import 'dart:convert';
import 'dart:math';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import '../core/network/api_client.dart';
import '../core/network/auth_http_client.dart';
import 'auth_storage_service.dart';
import 'settings_service.dart';
import 'sos_location_service.dart';

enum SosDeliveryState {
  queued,
  sending,
  serverReceived,
  acknowledgedByOperator,
  verified,
  cancelled,
  closed,
  failed,
}

class QueuedSosAlert {
  final String id;
  final String idempotencyKey;
  final String alertType; // 'sos', 'silent_sos', 'panic_button'
  final String serviceCategory; // 'general', 'police', 'fire', ...
  final String categorySource; // 'user_selected'
  double? latitude;
  double? longitude;
  double? accuracyM;
  String locationStatus;
  final DateTime triggeredAt;
  DateTime? receivedAt;
  int retryCount;
  SosDeliveryState deliveryState;
  String? operatorStatus; // 'pending', 'acknowledged', 'verified', 'closed', 'cancelled'

  QueuedSosAlert({
    required this.id,
    required this.idempotencyKey,
    required this.alertType,
    this.serviceCategory = 'general',
    this.categorySource = 'user_selected',
    this.latitude,
    this.longitude,
    this.accuracyM,
    required this.locationStatus,
    required this.triggeredAt,
    this.receivedAt,
    this.retryCount = 0,
    this.deliveryState = SosDeliveryState.queued,
    this.operatorStatus,
  });

  Map<String, dynamic> toJson() => {
        'id': id,
        'idempotency_key': idempotencyKey,
        'alert_type': alertType,
        'service_category': serviceCategory,
        'category_source': categorySource,
        'latitude': latitude,
        'longitude': longitude,
        'accuracy_m': accuracyM,
        'location_status': locationStatus,
        'triggered_at': triggeredAt.toIso8601String(),
        'received_at': receivedAt?.toIso8601String(),
        'retry_count': retryCount,
        'delivery_state': deliveryState.name,
        'operator_status': operatorStatus,
      };

  factory QueuedSosAlert.fromJson(Map<String, dynamic> json) => QueuedSosAlert(
        id: json['id'] as String,
        idempotencyKey: json['idempotency_key'] as String,
        alertType: json['alert_type'] as String,
        serviceCategory: json['service_category'] as String? ?? 'general',
        categorySource: json['category_source'] as String? ?? 'user_selected',
        latitude: (json['latitude'] as num?)?.toDouble(),
        longitude: (json['longitude'] as num?)?.toDouble(),
        accuracyM: (json['accuracy_m'] as num?)?.toDouble(),
        locationStatus: json['location_status'] as String? ?? 'unavailable',
        triggeredAt: DateTime.parse(json['triggered_at'] as String),
        receivedAt: json['received_at'] != null ? DateTime.parse(json['received_at'] as String) : null,
        retryCount: json['retry_count'] as int? ?? 0,
        deliveryState: SosDeliveryState.values.firstWhere(
          (e) => e.name == json['delivery_state'],
          orElse: () => SosDeliveryState.queued,
        ),
        operatorStatus: json['operator_status'] as String?,
      );
}

class SosQueueService {
  static final SosQueueService _instance = SosQueueService._internal();
  factory SosQueueService() => _instance;
  SosQueueService._internal();

  static const String _queueKey = 'sos_offline_queue_v1';
  static const String _activeAlertIdKey = 'sos_active_alert_id';
  static const String _lastTriggerTimeKey = 'sos_last_trigger_time';

  final _statusController = StreamController<QueuedSosAlert>.broadcast();
  Stream<QueuedSosAlert> get statusStream => _statusController.stream;

  QueuedSosAlert? _currentActiveAlert;
  QueuedSosAlert? get currentActiveAlert => _currentActiveAlert;

  Timer? _statusPollTimer;
  Timer? _liveLocationTimer;

  static String generateUuid() {
    final random = Random.secure();
    final bytes = List<int>.generate(16, (_) => random.nextInt(256));
    bytes[6] = (bytes[6] & 0x0f) | 0x40; // version 4
    bytes[8] = (bytes[8] & 0x3f) | 0x80; // variant
    final hex = bytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join();
    return '${hex.substring(0, 8)}-${hex.substring(8, 12)}-${hex.substring(12, 16)}-${hex.substring(16, 20)}-${hex.substring(20, 32)}';
  }

  static String generateIdempotencyKey() {
    final random = Random.secure();
    return List<int>.generate(16, (_) => random.nextInt(256))
        .map((b) => b.toRadixString(16).padLeft(2, '0'))
        .join();
  }

  Future<void> init() async {
    await _loadQueue();
    _processQueue();
  }

  Future<bool> isCoolingDown() async {
    final prefs = await SharedPreferences.getInstance();
    final lastTrigger = prefs.getInt(_lastTriggerTimeKey);
    if (lastTrigger == null) return false;
    final elapsed = DateTime.now().millisecondsSinceEpoch - lastTrigger;
    return elapsed < 30000; // 30-second anti-accident cooldown
  }

  Future<QueuedSosAlert> enqueueSos({
    required String alertType,
    String serviceCategory = 'general',
    String categorySource = 'user_selected',
    SosLocationFix? locationFix,
  }) async {
    final prefs = await SharedPreferences.getInstance();

    // 30s Cooldown check: if active alert exists within 30s, reuse it
    if (_currentActiveAlert != null &&
        (_currentActiveAlert!.deliveryState == SosDeliveryState.serverReceived ||
         _currentActiveAlert!.deliveryState == SosDeliveryState.acknowledgedByOperator)) {
      final elapsed = DateTime.now().difference(_currentActiveAlert!.triggeredAt).inSeconds;
      if (elapsed < 30) {
        debugPrint('[SosQueueService] 30s cooldown active, reusing alert ${_currentActiveAlert!.id}');
        return _currentActiveAlert!;
      }
    }

    final alert = QueuedSosAlert(
      id: generateUuid(),
      idempotencyKey: generateIdempotencyKey(),
      alertType: alertType,
      serviceCategory: serviceCategory,
      categorySource: categorySource,
      latitude: locationFix?.latitude,
      longitude: locationFix?.longitude,
      accuracyM: locationFix?.accuracyM,
      locationStatus: locationFix?.locationStatus ?? 'unavailable',
      triggeredAt: DateTime.now().toUtc(),
      deliveryState: SosDeliveryState.queued,
    );

    _currentActiveAlert = alert;
    await prefs.setInt(_lastTriggerTimeKey, DateTime.now().millisecondsSinceEpoch);
    await prefs.setString(_activeAlertIdKey, alert.id);

    await _saveAlertToQueue(alert);
    _statusController.add(alert);

    // Trigger immediate transmission attempt
    _dispatchAlert(alert);

    return alert;
  }

  Future<void> _dispatchAlert(QueuedSosAlert alert) async {
    alert.deliveryState = SosDeliveryState.sending;
    _statusController.add(alert);

    try {
      final body = {
        'id': alert.id,
        'idempotency_key': alert.idempotencyKey,
        'alert_type': alert.alertType,
        'service_category': alert.serviceCategory,
        'category_source': alert.categorySource,
        'latitude': alert.latitude,
        'longitude': alert.longitude,
        'accuracy_m': alert.accuracyM,
        'location_status': alert.locationStatus,
        'triggered_at': alert.triggeredAt.toIso8601String(),
        'app_version': '1.0.0',
      };

      final response = await AuthHttpClient.post(
        '/api/v1/sos',
        body: jsonEncode(body),
        timeout: const Duration(seconds: 15),
      );

      if (response.statusCode == 200 || response.statusCode == 201) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        alert.deliveryState = SosDeliveryState.serverReceived;
        alert.receivedAt = DateTime.tryParse(data['received_at'] ?? '') ?? DateTime.now().toUtc();
        alert.operatorStatus = data['status'] ?? 'pending';

        await _saveAlertToQueue(alert);
        _statusController.add(alert);

        // Start polling operator status and live location streaming if enabled in settings
        _startStatusPolling(alert.id);
        final settings = await SettingsService.load();
        if (settings.liveLocationEnabled) {
          _startLiveLocationUpdates(alert.id);
        }
      } else {
        _handleTransmissionFailure(alert);
      }
    } catch (e) {
      debugPrint('[SosQueueService] Transmission failed: $e');
      _handleTransmissionFailure(alert);
    }
  }

  void _handleTransmissionFailure(QueuedSosAlert alert) {
    alert.retryCount++;
    alert.deliveryState = SosDeliveryState.queued; // Offline / retry state
    _statusController.add(alert);
    _saveAlertToQueue(alert);

    // Exponential backoff retry
    final delaySeconds = min(pow(2, alert.retryCount).toInt(), 60);
    Timer(Duration(seconds: delaySeconds), () {
      if (alert.deliveryState == SosDeliveryState.queued) {
        _dispatchAlert(alert);
      }
    });
  }

  void _startStatusPolling(String alertId) {
    _statusPollTimer?.cancel();
    _statusPollTimer = Timer.periodic(const Duration(seconds: 5), (timer) async {
      try {
        final baseUrl = await ApiClient.getBaseUrl();
        final uri = Uri.parse('$baseUrl/api/v1/sos/$alertId/status');
        final token = await AuthStorageService.getAccessToken();

        final response = await http.get(uri, headers: {
          'Accept': 'application/json',
          if (token != null) 'Authorization': 'Bearer $token',
        }).timeout(const Duration(seconds: 10));

        if (response.statusCode == 200) {
          final data = jsonDecode(response.body) as Map<String, dynamic>;
          final opStatus = data['status'] as String?;
          if (_currentActiveAlert != null && _currentActiveAlert!.id == alertId) {
            _currentActiveAlert!.operatorStatus = opStatus;
            if (opStatus == 'acknowledged') {
              _currentActiveAlert!.deliveryState = SosDeliveryState.acknowledgedByOperator;
            } else if (opStatus == 'verified') {
              _currentActiveAlert!.deliveryState = SosDeliveryState.verified;
            } else if (opStatus == 'closed' || opStatus == 'cancelled' || opStatus == 'false_alarm') {
              _currentActiveAlert!.deliveryState = SosDeliveryState.closed;
              _stopLiveLocationUpdates();
              timer.cancel();
            }
            _statusController.add(_currentActiveAlert!);
            await _saveAlertToQueue(_currentActiveAlert!);
          }
        }
      } catch (e) {
        debugPrint('[SosQueueService] Status polling error: $e');
      }
    });
  }

  void _startLiveLocationUpdates(String alertId) {
    _liveLocationTimer?.cancel();
    _liveLocationTimer = Timer.periodic(const Duration(seconds: 12), (timer) async {
      try {
        final fix = await SosLocationService.captureLocation();
        if (fix.latitude != null && fix.longitude != null) {
          final baseUrl = await ApiClient.getBaseUrl();
          final uri = Uri.parse('$baseUrl/api/v1/sos/$alertId/location');
          final token = await AuthStorageService.getAccessToken();

          await http.post(
            uri,
            headers: {
              'Content-Type': 'application/json',
              if (token != null) 'Authorization': 'Bearer $token',
            },
            body: jsonEncode({
              'latitude': fix.latitude,
              'longitude': fix.longitude,
              'accuracy_m': fix.accuracyM,
              'recorded_at': fix.recordedAt.toIso8601String(),
            }),
          ).timeout(const Duration(seconds: 10));
        }
      } catch (_) {}
    });
  }

  void _stopLiveLocationUpdates() {
    _liveLocationTimer?.cancel();
    _liveLocationTimer = null;
  }

  Future<bool> cancelActiveAlert({String reason = 'User cancelled'}) async {
    if (_currentActiveAlert == null) return false;
    final alertId = _currentActiveAlert!.id;
    _stopLiveLocationUpdates();
    _statusPollTimer?.cancel();

    try {
      final baseUrl = await ApiClient.getBaseUrl();
      final uri = Uri.parse('$baseUrl/api/v1/sos/$alertId/cancel');
      final token = await AuthStorageService.getAccessToken();

      final res = await http.post(
        uri,
        headers: {
          'Content-Type': 'application/json',
          if (token != null) 'Authorization': 'Bearer $token',
        },
        body: jsonEncode({'reason': reason}),
      ).timeout(const Duration(seconds: 10));

      if (res.statusCode == 200) {
        _currentActiveAlert!.deliveryState = SosDeliveryState.cancelled;
        _currentActiveAlert!.operatorStatus = 'cancelled';
        _statusController.add(_currentActiveAlert!);
        await _saveAlertToQueue(_currentActiveAlert!);
        return true;
      }
    } catch (e) {
      debugPrint('[SosQueueService] Cancel call failed: $e');
    }
    return false;
  }

  Future<void> _saveAlertToQueue(QueuedSosAlert alert) async {
    final prefs = await SharedPreferences.getInstance();
    final queue = await _loadQueue();
    final index = queue.indexWhere((a) => a.id == alert.id);
    if (index >= 0) {
      queue[index] = alert;
    } else {
      queue.add(alert);
    }
    final rawList = queue.map((a) => jsonEncode(a.toJson())).toList();
    await prefs.setStringList(_queueKey, rawList);
  }

  Future<List<QueuedSosAlert>> _loadQueue() async {
    final prefs = await SharedPreferences.getInstance();
    final rawList = prefs.getStringList(_queueKey) ?? [];
    return rawList.map((str) => QueuedSosAlert.fromJson(jsonDecode(str))).toList();
  }

  Future<void> _processQueue() async {
    final queue = await _loadQueue();
    for (final alert in queue) {
      if (alert.deliveryState == SosDeliveryState.queued) {
        _dispatchAlert(alert);
      }
    }
  }

  Future<void> clearQueue() async {
    _statusPollTimer?.cancel();
    _liveLocationTimer?.cancel();
    _currentActiveAlert = null;
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_queueKey);
    await prefs.remove(_activeAlertIdKey);
    await prefs.remove(_lastTriggerTimeKey);
  }

  void dispose() {
    _statusPollTimer?.cancel();
    _liveLocationTimer?.cancel();
    _statusController.close();
  }
}
