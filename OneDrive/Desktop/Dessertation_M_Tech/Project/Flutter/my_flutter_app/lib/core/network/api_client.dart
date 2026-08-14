import 'package:http/http.dart' as http;

import 'backend_discovery.dart';

class ApiClient {
  static final BackendDiscovery _discovery = BackendDiscovery();

  /// Resolves the backend once at startup (and again when Wi-Fi reconnects).
  static Future<void> init() => _discovery.ensureResolved();

  /// Returns the resolved backend URL, discovering it if needed.
  static Future<String> getBaseUrl() => _discovery.ensureResolved();

  /// Last resolved URL (call [init] or [getBaseUrl] first).
  static String get baseUrl => BackendDiscovery.baseUrl;

  /// Re-scan when network conditions change (e.g. Wi-Fi connected).
  static Future<String> refreshBaseUrl() => _discovery.refresh();

  static final http.Client client = http.Client();
}
