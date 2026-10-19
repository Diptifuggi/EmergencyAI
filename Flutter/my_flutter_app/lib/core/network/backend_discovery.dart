import 'dart:async';
import 'dart:io' show Platform;

import 'package:flutter/foundation.dart' show debugPrint, kDebugMode, kIsWeb;
import 'package:http/http.dart' as http;
import 'package:network_info_plus/network_info_plus.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'api_config.dart';

/// Finds the EmergencyIQ FastAPI backend without hard-coded PC IPs.
///
/// Order: build-time override → cached URL → USB localhost (`adb reverse`) →
/// emulator host → parallel Wi-Fi subnet scan for `/api/v1/health`.
class BackendDiscovery {
  BackendDiscovery({http.Client? client}) : _client = client ?? http.Client();

  static const cacheKey = 'emergencyiq_api_base_url';
  static const port = 8000;
  static const configuredBackend = ApiConfig.defaultBaseUrl;
  static const emulatorBackend = ApiConfig.androidEmulatorBaseUrl;
  static const adbReverseBackend = ApiConfig.adbReverseBaseUrl;
  static const healthPath = ApiConfig.healthEndpoint;
  static const connectTimeout = Duration(milliseconds: 900);
  static const scanBatchSize = 24;

  final http.Client _client;
  Future<String>? _resolveFuture;
  static String? resolved;

  void _log(String message) {
    if (kDebugMode) debugPrint('[Backend] $message');
  }

  static Future<String> resolveBaseUrl({http.Client? client}) {
    return BackendDiscovery(client: client).ensureResolved();
  }

  static List<String> candidateBackends() {
    return [
      adbReverseBackend,
      emulatorBackend,
    ];
  }

  static Future<String?> selectHealthyBackend({
    required List<String> candidates,
    required Future<bool> Function(String candidate) probe,
  }) async {
    for (final candidate in candidates) {
      final normalized = normalizeBaseUrl(candidate);
      final healthy = await probe(normalized);
      if (healthy) {
        return normalized;
      }
    }
    return null;
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
      resolved = adbReverseBackend;
      _log('FLUTTER_TEST resolved to $resolved');
      return resolved!;
    }

    const fromEnv = ApiConfig.baseUrlOverride;
    if (fromEnv.isNotEmpty) {
      resolved = normalizeBaseUrl(fromEnv);
      _log('Using API_BASE_URL override.');
      return resolved!;
    }

    final prefs = await SharedPreferences.getInstance();
    final cached = prefs.getString(cacheKey);
    if (cached != null) {
      final normalized = normalizeBaseUrl(cached);
      if (await _isHealthy(normalized)) {
        resolved = normalized;
        _log('Using healthy cached backend.');
        return resolved!;
      }
    }

    final candidates = candidateBackends();
    final selected = await selectHealthyBackend(
      candidates: candidates,
      probe: (candidate) => _isHealthy(candidate),
    );

    if (selected != null) {
      await _remember(prefs, selected);
      resolved = selected;
      _log('Selected a healthy backend.');
      return resolved!;
    }

    if (!kIsWeb && (Platform.isAndroid || Platform.isIOS)) {
      final subnetHit = await _discoverOnWifiSubnet(prefs);
      if (subnetHit != null) {
        resolved = subnetHit;
        _log('Selected a backend from Wi-Fi discovery.');
        return resolved!;
      }
    }

    resolved = configuredBackend;
    _log(
      'No healthy backend found; using the configured default. '
      'Physical Android can use API_BASE_URL or automatic Wi-Fi discovery.',
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
      _log('Scanning the connected Wi-Fi subnet for the backend.');

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
            _log('Backend discovered on Wi-Fi.');
            return resolved;
          }
        }
      }
    } catch (error) {
      _log('Wi-Fi discovery skipped (${error.runtimeType}).');
    }
    return null;
  }

  Future<void> _remember(SharedPreferences prefs, String url) async {
    resolved = normalizeBaseUrl(url);
    await prefs.setString(cacheKey, resolved!);
  }

  Future<bool> _isHealthy(String baseUrl) async {
    final normalized = normalizeBaseUrl(baseUrl);
    final uri = Uri.parse('$normalized$healthPath');
    _log('Checking backend health.');

    try {
      final response = await _client
          .get(uri, headers: {'Accept': 'application/json'})
          .timeout(connectTimeout);
      final isOk = response.statusCode == 200 &&
          response.body.contains('"status"') &&
          response.body.contains('ok');
      _log('Health check ${isOk ? 'passed' : 'failed'} (HTTP ${response.statusCode}).');
      return isOk;
    } catch (error) {
      _log('Health check failed (${error.runtimeType}).');
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

  static String get baseUrl => resolved ?? configuredBackend;
}
