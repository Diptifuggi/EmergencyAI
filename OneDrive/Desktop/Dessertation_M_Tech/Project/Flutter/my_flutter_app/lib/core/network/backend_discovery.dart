import 'dart:async';
import 'dart:io' show Platform;

import 'package:flutter/foundation.dart' show debugPrint, kIsWeb;
import 'package:http/http.dart' as http;
import 'package:network_info_plus/network_info_plus.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Finds the EmergencyIQ FastAPI backend without hard-coded PC IPs.
///
/// Order: build-time override → cached URL → USB localhost (`adb reverse`) →
/// emulator host → parallel Wi-Fi subnet scan for `/api/v1/health`.
class BackendDiscovery {
  BackendDiscovery({http.Client? client}) : _client = client ?? http.Client();

  static const cacheKey = 'emergencyiq_api_base_url';
  static const port = 8000;
  static const healthPath = '/api/v1/health';
  static const connectTimeout = Duration(milliseconds: 900);
  static const scanBatchSize = 24;

  final http.Client _client;
  Future<String>? _resolveFuture;
  static String? resolved;

  static Future<String> resolveBaseUrl({http.Client? client}) {
    return BackendDiscovery(client: client).ensureResolved();
  }

  Future<String> ensureResolved() {
    _resolveFuture ??= _resolve();
    return _resolveFuture!;
  }

  Future<String> refresh() async {
    _resolveFuture = null;
    resolved = null;
    return ensureResolved();
  }

  Future<String> _resolve() async {
    if (!kIsWeb && Platform.environment.containsKey('FLUTTER_TEST')) {
      resolved = 'http://127.0.0.1:$port';
      return resolved!;
    }

    const fromEnv = String.fromEnvironment('API_BASE_URL');
    if (fromEnv.isNotEmpty) {
      resolved = normalizeBaseUrl(fromEnv);
      debugPrint('[EmergencyIQ] Backend from API_BASE_URL: $resolved');
      return resolved!;
    }

    final prefs = await SharedPreferences.getInstance();
    final cached = prefs.getString(cacheKey);
    if (cached != null && await _isHealthy(cached)) {
      resolved = normalizeBaseUrl(cached);
      debugPrint('[EmergencyIQ] Backend from cache: $resolved');
      return resolved!;
    }

    final quickCandidates = <String>[
      'http://127.0.0.1:$port',
      'http://10.0.2.2:$port',
    ];

    for (final candidate in quickCandidates) {
      if (await _isHealthy(candidate)) {
        await _remember(prefs, candidate);
        return resolved!;
      }
    }

    if (!kIsWeb && (Platform.isAndroid || Platform.isIOS)) {
      final subnetHit = await _discoverOnWifiSubnet(prefs);
      if (subnetHit != null) {
        return subnetHit;
      }
    }

    resolved = 'http://127.0.0.1:$port';
    debugPrint(
      '[EmergencyIQ] Backend discovery failed; fallback $resolved '
      '(use USB + adb reverse or same Wi-Fi as PC)',
    );
    return resolved!;
  }

  Future<String?> _discoverOnWifiSubnet(SharedPreferences prefs) async {
    try {
      final wifiIp = await NetworkInfo().getWifiIP();
      if (wifiIp == null || wifiIp.isEmpty || wifiIp == '0.0.0.0') {
        return null;
      }

      final parts = wifiIp.split('.');
      if (parts.length != 4) return null;

      final prefix = '${parts[0]}.${parts[1]}.${parts[2]}';
      debugPrint('[EmergencyIQ] Scanning Wi-Fi subnet $prefix.0/24 for backend');

      final hosts = prioritizedHosts();
      for (var start = 0; start < hosts.length; start += scanBatchSize) {
        final batch = hosts.skip(start).take(scanBatchSize).toList();
        final hits = await Future.wait(
          batch.map((host) async {
            final url = 'http://$prefix.$host:$port';
            return (await _isHealthy(url)) ? url : null;
          }),
        );

        for (final hit in hits) {
          if (hit != null) {
            await _remember(prefs, hit);
            debugPrint('[EmergencyIQ] Backend discovered on Wi-Fi: $resolved');
            return resolved;
          }
        }
      }
    } catch (error) {
      debugPrint('[EmergencyIQ] Wi-Fi discovery skipped: $error');
    }
    return null;
  }

  Future<void> _remember(SharedPreferences prefs, String url) async {
    resolved = normalizeBaseUrl(url);
    await prefs.setString(cacheKey, resolved!);
  }

  Future<bool> _isHealthy(String baseUrl) async {
    try {
      final uri = Uri.parse('${normalizeBaseUrl(baseUrl)}$healthPath');
      final response = await _client
          .get(uri, headers: {'Accept': 'application/json'})
          .timeout(connectTimeout);
      if (response.statusCode != 200) return false;
      final body = response.body;
      return body.contains('"status"') && body.contains('ok');
    } catch (_) {
      return false;
    }
  }

  static String normalizeBaseUrl(String url) {
    final trimmed = url.trim().replaceAll(RegExp(r'/$'), '');
    if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) {
      return trimmed;
    }
    return 'http://$trimmed';
  }

  static List<int> prioritizedHosts() {
    final hosts = <int>{};
    for (final host in [1, 2, 254, 100, 101, 102, 103, 196, 200, 202]) {
      hosts.add(host);
    }
    for (var host = 1; host <= 254; host++) {
      hosts.add(host);
    }
    return hosts.toList();
  }

  static String get baseUrl => resolved ?? 'http://127.0.0.1:$port';
}
