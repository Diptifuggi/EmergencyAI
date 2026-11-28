import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';

import '../core/network/auth_http_client.dart';

class HomeFeatureApiService {
  static const _cachedAddressKey = 'last_resolved_address_v1';

  // --- Reverse Geocoding with local cache ---
  static Future<String?> getCachedAddress() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_cachedAddressKey);
  }

  static Future<String?> reverseGeocode(double lat, double lon) async {
    try {
      final resp = await AuthHttpClient.get(
        '/api/v1/location/reverse?lat=$lat&lon=$lon',
        timeout: const Duration(seconds: 10),
      );
      if (resp.statusCode == 200) {
        final data = jsonDecode(resp.body) as Map<String, dynamic>;
        final addr = data['address'] as String?;
        if (addr != null && addr.trim().isNotEmpty) {
          final prefs = await SharedPreferences.getInstance();
          await prefs.setString(_cachedAddressKey, addr.trim());
          return addr.trim();
        }
      }
    } catch (_) {}
    return getCachedAddress();
  }

  // --- My Voice / Text Emergency Reports ---
  static Future<Map<String, dynamic>> listMyEmergencyCalls({int limit = 30, int offset = 0}) async {
    final resp = await AuthHttpClient.get('/api/v1/emergency-calls/mine?limit=$limit&offset=$offset');
    if (resp.statusCode == 200) {
      return jsonDecode(resp.body) as Map<String, dynamic>;
    }
    throw Exception('Failed to load reports (${resp.statusCode})');
  }

  // --- SOS History (Mine) ---
  static Future<Map<String, dynamic>> listMySosAlerts({int page = 1, int pageSize = 20}) async {
    final resp = await AuthHttpClient.get('/api/v1/sos/mine?page=$page&page_size=$pageSize');
    if (resp.statusCode == 200) {
      return jsonDecode(resp.body) as Map<String, dynamic>;
    }
    throw Exception('Failed to load SOS history (${resp.statusCode})');
  }

  static Future<Map<String, dynamic>> getMySosDetail(String alertId) async {
    final resp = await AuthHttpClient.get('/api/v1/sos/mine/$alertId');
    if (resp.statusCode == 200) {
      return jsonDecode(resp.body) as Map<String, dynamic>;
    }
    throw Exception('Failed to load SOS detail (${resp.statusCode})');
  }

  static Future<void> cancelSosAlert(String alertId, {String reason = 'Cancelled by user'}) async {
    final resp = await AuthHttpClient.post(
      '/api/v1/sos/$alertId/cancel',
      body: jsonEncode({'reason': reason}),
    );
    if (resp.statusCode != 200) {
      throw Exception('Failed to cancel SOS (${resp.statusCode})');
    }
  }

  // --- Emergency Contacts ---
  static Future<List<Map<String, dynamic>>> listEmergencyContacts() async {
    final resp = await AuthHttpClient.get('/api/v1/users/me/emergency-contacts');
    if (resp.statusCode == 200) {
      final list = jsonDecode(resp.body) as List<dynamic>;
      return list.cast<Map<String, dynamic>>();
    }
    throw Exception('Failed to load emergency contacts (${resp.statusCode})');
  }

  static Future<Map<String, dynamic>> createEmergencyContact(Map<String, dynamic> payload) async {
    final resp = await AuthHttpClient.post(
      '/api/v1/users/me/emergency-contacts',
      body: jsonEncode(payload),
    );
    if (resp.statusCode == 201 || resp.statusCode == 200) {
      return jsonDecode(resp.body) as Map<String, dynamic>;
    }
    final err = _extractError(resp.body);
    throw Exception(err ?? 'Failed to add emergency contact (${resp.statusCode})');
  }

  static Future<Map<String, dynamic>> updateEmergencyContact(String id, Map<String, dynamic> payload) async {
    final resp = await AuthHttpClient.put(
      '/api/v1/users/me/emergency-contacts/$id',
      body: jsonEncode(payload),
    );
    if (resp.statusCode == 200) {
      return jsonDecode(resp.body) as Map<String, dynamic>;
    }
    final err = _extractError(resp.body);
    throw Exception(err ?? 'Failed to update contact (${resp.statusCode})');
  }

  static Future<void> deleteEmergencyContact(String id) async {
    final resp = await AuthHttpClient.delete('/api/v1/users/me/emergency-contacts/$id');
    if (resp.statusCode != 200) {
      throw Exception('Failed to delete contact (${resp.statusCode})');
    }
  }

  // --- Notifications ---
  static Future<Map<String, dynamic>> listNotifications({int page = 1, int pageSize = 30}) async {
    final resp = await AuthHttpClient.get('/api/v1/users/me/notifications?page=$page&page_size=$pageSize');
    if (resp.statusCode == 200) {
      return jsonDecode(resp.body) as Map<String, dynamic>;
    }
    throw Exception('Failed to load notifications (${resp.statusCode})');
  }

  static Future<int> getUnreadNotificationCount() async {
    try {
      final resp = await AuthHttpClient.get(
        '/api/v1/users/me/notifications/unread-count',
        timeout: const Duration(seconds: 8),
      );
      if (resp.statusCode == 200) {
        final data = jsonDecode(resp.body) as Map<String, dynamic>;
        return (data['unread_count'] as num?)?.toInt() ?? 0;
      }
    } catch (_) {}
    return 0;
  }

  static Future<void> markNotificationRead(String id) async {
    await AuthHttpClient.post('/api/v1/users/me/notifications/$id/read');
  }

  static Future<void> markAllNotificationsRead() async {
    await AuthHttpClient.post('/api/v1/users/me/notifications/read-all');
  }

  // --- TrackMe ---
  static Future<Map<String, dynamic>> startTrackSession({
    required int durationHours,
    bool shareWithControlRoom = false,
    String? sosAlertId,
    double? latitude,
    double? longitude,
    double? accuracyM,
  }) async {
    final resp = await AuthHttpClient.post(
      '/api/v1/track/start',
      body: jsonEncode({
        'duration_hours': durationHours,
        'share_with_control_room': shareWithControlRoom,
        if (sosAlertId != null) 'sos_alert_id': sosAlertId,
        'latitude': latitude,
        'longitude': longitude,
        'accuracy_m': accuracyM,
      }),
    );
    if (resp.statusCode == 201 || resp.statusCode == 200) {
      return jsonDecode(resp.body) as Map<String, dynamic>;
    }
    throw Exception('Failed to start TrackMe (${resp.statusCode})');
  }

  static Future<bool> sendTrackPointsBatch(
    String sessionId,
    List<Map<String, dynamic>> points,
  ) async {
    final resp = await AuthHttpClient.post(
      '/api/v1/track/$sessionId/points',
      body: jsonEncode({'points': points}),
      timeout: const Duration(seconds: 10),
    );
    return resp.statusCode == 200;
  }

  static Future<void> attachSosToTrackSession(String sessionId, String sosAlertId) async {
    await AuthHttpClient.post(
      '/api/v1/track/$sessionId/attach-sos',
      body: jsonEncode({'sos_alert_id': sosAlertId}),
      timeout: const Duration(seconds: 10),
    );
  }

  static Future<void> sendTrackPoint(
    String sessionId, {
    required double latitude,
    required double longitude,
    double? accuracyM,
    String? clientPointId,
    DateTime? recordedAt,
  }) async {
    await AuthHttpClient.post(
      '/api/v1/track/$sessionId/points',
      body: jsonEncode({
        if (clientPointId != null) 'client_point_id': clientPointId,
        'latitude': latitude,
        'longitude': longitude,
        'accuracy_m': accuracyM,
        if (recordedAt != null) 'recorded_at': recordedAt.toUtc().toIso8601String(),
      }),
      timeout: const Duration(seconds: 10),
    );
  }

  static Future<Map<String, dynamic>> stopTrackSession(String sessionId) async {
    final resp = await AuthHttpClient.post('/api/v1/track/$sessionId/stop');
    if (resp.statusCode == 200) {
      return jsonDecode(resp.body) as Map<String, dynamic>;
    }
    throw Exception('Failed to stop TrackMe (${resp.statusCode})');
  }

  static String? _extractError(String body) {
    try {
      final decoded = jsonDecode(body);
      if (decoded is Map<String, dynamic> && decoded['detail'] != null) {
        return decoded['detail'].toString();
      }
    } catch (_) {}
    return null;
  }
}
