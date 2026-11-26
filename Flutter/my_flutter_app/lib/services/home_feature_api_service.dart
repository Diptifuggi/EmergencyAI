import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import '../core/network/api_client.dart';
import 'auth_storage_service.dart';

class HomeFeatureApiService {
  static const _cachedAddressKey = 'last_resolved_address_v1';

  static Future<Map<String, String>> _authHeaders() async {
    final token = await AuthStorageService.getAccessToken();
    return {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      if (token != null && token.isNotEmpty) 'Authorization': 'Bearer $token',
    };
  }

  // --- Reverse Geocoding with local cache ---
  static Future<String?> getCachedAddress() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_cachedAddressKey);
  }

  static Future<String?> reverseGeocode(double lat, double lon) async {
    try {
      final baseUrl = await ApiClient.getBaseUrl();
      final uri = Uri.parse('$baseUrl/api/v1/location/reverse?lat=$lat&lon=$lon');
      final resp = await http.get(uri, headers: await _authHeaders()).timeout(const Duration(seconds: 10));
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

  // --- SOS History (Mine) ---
  static Future<Map<String, dynamic>> listMySosAlerts({int page = 1, int pageSize = 20}) async {
    final baseUrl = await ApiClient.getBaseUrl();
    final uri = Uri.parse('$baseUrl/api/v1/sos/mine?page=$page&page_size=$pageSize');
    final resp = await http.get(uri, headers: await _authHeaders()).timeout(const Duration(seconds: 12));
    if (resp.statusCode == 200) {
      return jsonDecode(resp.body) as Map<String, dynamic>;
    }
    throw Exception('Failed to load SOS history (${resp.statusCode})');
  }

  static Future<Map<String, dynamic>> getMySosDetail(String alertId) async {
    final baseUrl = await ApiClient.getBaseUrl();
    final uri = Uri.parse('$baseUrl/api/v1/sos/mine/$alertId');
    final resp = await http.get(uri, headers: await _authHeaders()).timeout(const Duration(seconds: 12));
    if (resp.statusCode == 200) {
      return jsonDecode(resp.body) as Map<String, dynamic>;
    }
    throw Exception('Failed to load SOS detail (${resp.statusCode})');
  }

  static Future<void> cancelSosAlert(String alertId, {String reason = 'Cancelled by user'}) async {
    final baseUrl = await ApiClient.getBaseUrl();
    final uri = Uri.parse('$baseUrl/api/v1/sos/$alertId/cancel');
    final resp = await http
        .post(uri, headers: await _authHeaders(), body: jsonEncode({'reason': reason}))
        .timeout(const Duration(seconds: 12));
    if (resp.statusCode != 200) {
      throw Exception('Failed to cancel SOS (${resp.statusCode})');
    }
  }

  // --- Emergency Contacts ---
  static Future<List<Map<String, dynamic>>> listEmergencyContacts() async {
    final baseUrl = await ApiClient.getBaseUrl();
    final uri = Uri.parse('$baseUrl/api/v1/users/me/emergency-contacts');
    final resp = await http.get(uri, headers: await _authHeaders()).timeout(const Duration(seconds: 12));
    if (resp.statusCode == 200) {
      final list = jsonDecode(resp.body) as List<dynamic>;
      return list.cast<Map<String, dynamic>>();
    }
    throw Exception('Failed to load emergency contacts (${resp.statusCode})');
  }

  static Future<Map<String, dynamic>> createEmergencyContact(Map<String, dynamic> payload) async {
    final baseUrl = await ApiClient.getBaseUrl();
    final uri = Uri.parse('$baseUrl/api/v1/users/me/emergency-contacts');
    final resp = await http
        .post(uri, headers: await _authHeaders(), body: jsonEncode(payload))
        .timeout(const Duration(seconds: 12));
    if (resp.statusCode == 201 || resp.statusCode == 200) {
      return jsonDecode(resp.body) as Map<String, dynamic>;
    }
    final err = _extractError(resp.body);
    throw Exception(err ?? 'Failed to add emergency contact (${resp.statusCode})');
  }

  static Future<Map<String, dynamic>> updateEmergencyContact(String id, Map<String, dynamic> payload) async {
    final baseUrl = await ApiClient.getBaseUrl();
    final uri = Uri.parse('$baseUrl/api/v1/users/me/emergency-contacts/$id');
    final resp = await http
        .put(uri, headers: await _authHeaders(), body: jsonEncode(payload))
        .timeout(const Duration(seconds: 12));
    if (resp.statusCode == 200) {
      return jsonDecode(resp.body) as Map<String, dynamic>;
    }
    final err = _extractError(resp.body);
    throw Exception(err ?? 'Failed to update contact (${resp.statusCode})');
  }

  static Future<void> deleteEmergencyContact(String id) async {
    final baseUrl = await ApiClient.getBaseUrl();
    final uri = Uri.parse('$baseUrl/api/v1/users/me/emergency-contacts/$id');
    final resp = await http.delete(uri, headers: await _authHeaders()).timeout(const Duration(seconds: 12));
    if (resp.statusCode != 200) {
      throw Exception('Failed to delete contact (${resp.statusCode})');
    }
  }

  // --- Notifications ---
  static Future<Map<String, dynamic>> listNotifications({int page = 1, int pageSize = 30}) async {
    final baseUrl = await ApiClient.getBaseUrl();
    final uri = Uri.parse('$baseUrl/api/v1/users/me/notifications?page=$page&page_size=$pageSize');
    final resp = await http.get(uri, headers: await _authHeaders()).timeout(const Duration(seconds: 12));
    if (resp.statusCode == 200) {
      return jsonDecode(resp.body) as Map<String, dynamic>;
    }
    throw Exception('Failed to load notifications (${resp.statusCode})');
  }

  static Future<int> getUnreadNotificationCount() async {
    try {
      final baseUrl = await ApiClient.getBaseUrl();
      final uri = Uri.parse('$baseUrl/api/v1/users/me/notifications/unread-count');
      final resp = await http.get(uri, headers: await _authHeaders()).timeout(const Duration(seconds: 8));
      if (resp.statusCode == 200) {
        final data = jsonDecode(resp.body) as Map<String, dynamic>;
        return (data['unread_count'] as num?)?.toInt() ?? 0;
      }
    } catch (_) {}
    return 0;
  }

  static Future<void> markNotificationRead(String id) async {
    final baseUrl = await ApiClient.getBaseUrl();
    final uri = Uri.parse('$baseUrl/api/v1/users/me/notifications/$id/read');
    await http.post(uri, headers: await _authHeaders()).timeout(const Duration(seconds: 10));
  }

  static Future<void> markAllNotificationsRead() async {
    final baseUrl = await ApiClient.getBaseUrl();
    final uri = Uri.parse('$baseUrl/api/v1/users/me/notifications/read-all');
    await http.post(uri, headers: await _authHeaders()).timeout(const Duration(seconds: 10));
  }

  // --- TrackMe ---
  static Future<Map<String, dynamic>> startTrackSession({
    required int durationHours,
    double? latitude,
    double? longitude,
    double? accuracyM,
  }) async {
    final baseUrl = await ApiClient.getBaseUrl();
    final uri = Uri.parse('$baseUrl/api/v1/track/start');
    final resp = await http
        .post(
          uri,
          headers: await _authHeaders(),
          body: jsonEncode({
            'duration_hours': durationHours,
            'latitude': latitude,
            'longitude': longitude,
            'accuracy_m': accuracyM,
          }),
        )
        .timeout(const Duration(seconds: 12));
    if (resp.statusCode == 201 || resp.statusCode == 200) {
      return jsonDecode(resp.body) as Map<String, dynamic>;
    }
    throw Exception('Failed to start TrackMe (${resp.statusCode})');
  }

  static Future<void> sendTrackPoint(
    String sessionId, {
    required double latitude,
    required double longitude,
    double? accuracyM,
  }) async {
    final baseUrl = await ApiClient.getBaseUrl();
    final uri = Uri.parse('$baseUrl/api/v1/track/$sessionId/points');
    await http
        .post(
          uri,
          headers: await _authHeaders(),
          body: jsonEncode({
            'latitude': latitude,
            'longitude': longitude,
            'accuracy_m': accuracyM,
          }),
        )
        .timeout(const Duration(seconds: 10));
  }

  static Future<Map<String, dynamic>> stopTrackSession(String sessionId) async {
    final baseUrl = await ApiClient.getBaseUrl();
    final uri = Uri.parse('$baseUrl/api/v1/track/$sessionId/stop');
    final resp = await http.post(uri, headers: await _authHeaders()).timeout(const Duration(seconds: 12));
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
