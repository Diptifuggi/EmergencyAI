import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:geolocator/geolocator.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../core/network/api_client.dart';
import 'home_feature_api_service.dart';
import 'sos_location_service.dart';
import 'sos_queue_service.dart';

enum TrackMeState { idle, active, stale, offlineQueued, ended }

class TrackMeService {
  static final TrackMeService _instance = TrackMeService._internal();
  factory TrackMeService() => _instance;
  TrackMeService._internal();

  static const _bufferKey = 'trackme_offline_points_v1';
  static const _sessionKey = 'trackme_active_session_v1';

  final ValueNotifier<TrackMeState> stateNotifier = ValueNotifier(TrackMeState.idle);
  final ValueNotifier<int> queuedCountNotifier = ValueNotifier(0);

  Map<String, dynamic>? activeSession;
  String? shareUrl;
  Timer? _timer;
  StreamSubscription<Position>? _posSub;
  StreamSubscription<QueuedSosAlert>? _sosSub;
  int? lastBatteryPct;

  Future<void> init() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_sessionKey);
    if (raw != null) {
      try {
        activeSession = jsonDecode(raw) as Map<String, dynamic>;
        final expiresAt = DateTime.tryParse(activeSession?['expires_at']?.toString() ?? '');
        if (expiresAt != null && expiresAt.isBefore(DateTime.now().toUtc())) {
          await _handleExpired();
        } else if (activeSession != null) {
          stateNotifier.value = TrackMeState.active;
          _startTimersAndStreams();
        }
      } catch (_) {}
    }
    _listenForActiveSos();
  }

  void _listenForActiveSos() {
    _sosSub?.cancel();
    _sosSub = SosQueueService().statusStream.listen((alert) async {
      if (activeSession != null &&
          (alert.deliveryState == SosDeliveryState.serverReceived ||
              alert.deliveryState == SosDeliveryState.acknowledgedByOperator)) {
        try {
          await HomeFeatureApiService.attachSosToTrackSession(
            activeSession!['id'].toString(),
            alert.id,
          );
        } catch (_) {}
      }
    });
  }

  Future<void> startSession({
    required int durationHours,
    required bool shareWithControlRoom,
    required double latitude,
    required double longitude,
    double? accuracyM,
  }) async {
    final currentSos = SosQueueService().currentActiveAlert;
    final sosId = (currentSos != null &&
            (currentSos.deliveryState == SosDeliveryState.serverReceived ||
                currentSos.deliveryState == SosDeliveryState.acknowledgedByOperator))
        ? currentSos.id
        : null;

    final session = await HomeFeatureApiService.startTrackSession(
      durationHours: durationHours,
      shareWithControlRoom: shareWithControlRoom,
      sosAlertId: sosId,
      latitude: latitude,
      longitude: longitude,
      accuracyM: accuracyM,
    );

    final baseUrl = await ApiClient.getBaseUrl();
    final dashboardBase = baseUrl.replaceFirst(':8000', ':5173');
    shareUrl = '$dashboardBase/track/${session['share_token']}';
    activeSession = session;

    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_sessionKey, jsonEncode(session));
    stateNotifier.value = TrackMeState.active;

    _startTimersAndStreams();
  }

  void _startTimersAndStreams() {
    _timer?.cancel();
    _posSub?.cancel();

    // Foreground location stream on Android/iOS with foreground notification config
    try {
      final LocationSettings settings = defaultTargetPlatform == TargetPlatform.android
          ? AndroidSettings(
              accuracy: LocationAccuracy.high,
              distanceFilter: 10,
              intervalDuration: Duration(seconds: (lastBatteryPct != null && lastBatteryPct! <= 20) ? 30 : 15),
              foregroundNotificationConfig: const ForegroundNotificationConfig(
                notificationText: 'EmergencyIQ TrackMe is sharing your live location.',
                notificationTitle: 'TrackMe Active',
                enableWakeLock: true,
              ),
            )
          : AppleSettings(
              accuracy: LocationAccuracy.high,
              distanceFilter: 10,
              allowBackgroundLocationUpdates: true,
              showBackgroundLocationIndicator: true,
            );
      _posSub = Geolocator.getPositionStream(locationSettings: settings).listen((_) {});
    } catch (_) {}

    final intervalSec = (lastBatteryPct != null && lastBatteryPct! <= 20) ? 30 : 15;
    _timer = Timer.periodic(Duration(seconds: intervalSec), (_) => _tick());
  }

  Future<void> _tick() async {
    if (activeSession == null) return;
    final expiresAt = DateTime.tryParse(activeSession!['expires_at']?.toString() ?? '');
    if (expiresAt != null && expiresAt.isBefore(DateTime.now().toUtc())) {
      await _handleExpired();
      return;
    }

    final fix = await SosLocationService.captureLocation(promptIfDenied: false);
    if (fix.latitude == null || fix.longitude == null) {
      stateNotifier.value = TrackMeState.stale;
      return;
    }

    final pt = {
      'client_point_id': SosQueueService.generateUuid(),
      'latitude': fix.latitude,
      'longitude': fix.longitude,
      'accuracy_m': fix.accuracyM,
      'recorded_at': DateTime.now().toUtc().toIso8601String(),
    };

    await _enqueueAndFlushPoint(pt);
  }

  Future<void> _enqueueAndFlushPoint(Map<String, dynamic> pt) async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getStringList(_bufferKey) ?? [];
    final queue = raw.map((e) => jsonDecode(e) as Map<String, dynamic>).toList();
    queue.add(pt);

    try {
      final batch = queue.take(50).toList();
      final ok = await HomeFeatureApiService.sendTrackPointsBatch(
        activeSession!['id'].toString(),
        batch,
      );
      if (ok) {
        final remaining = queue.skip(batch.length).toList();
        await prefs.setStringList(_bufferKey, remaining.map((e) => jsonEncode(e)).toList());
        queuedCountNotifier.value = remaining.length;
        stateNotifier.value = remaining.isEmpty ? TrackMeState.active : TrackMeState.offlineQueued;
        return;
      }
    } catch (_) {}

    await prefs.setStringList(_bufferKey, queue.map((e) => jsonEncode(e)).toList());
    queuedCountNotifier.value = queue.length;
    stateNotifier.value = TrackMeState.offlineQueued;
  }

  Future<void> _handleExpired() async {
    _timer?.cancel();
    _posSub?.cancel();
    activeSession = null;
    shareUrl = null;
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_sessionKey);
    await prefs.remove(_bufferKey);
    queuedCountNotifier.value = 0;
    stateNotifier.value = TrackMeState.ended;
  }

  Future<void> stopSession() async {
    _timer?.cancel();
    _posSub?.cancel();
    if (activeSession != null) {
      try {
        await HomeFeatureApiService.stopTrackSession(activeSession!['id'].toString());
      } catch (_) {}
    }
    activeSession = null;
    shareUrl = null;
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_sessionKey);
    await prefs.remove(_bufferKey);
    queuedCountNotifier.value = 0;
    stateNotifier.value = TrackMeState.ended;
  }
}
