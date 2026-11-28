import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

import '../../screens/login_screen.dart';
import '../../services/auth_storage_service.dart';
import 'api_client.dart';

class AuthHttpClient {
  static final GlobalKey<NavigatorState> navigatorKey = GlobalKey<NavigatorState>();
  static Future<bool>? _refreshFuture;

  static Future<Map<String, String>> _buildHeaders(Map<String, String>? extra) async {
    final token = await AuthStorageService.getAccessToken();
    return {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      if (token != null && token.isNotEmpty) 'Authorization': 'Bearer $token',
      if (extra != null) ...extra,
    };
  }

  static Future<bool> _refreshTokens() async {
    if (_refreshFuture != null) return _refreshFuture!;
    _refreshFuture = _doRefresh();
    try {
      return await _refreshFuture!;
    } finally {
      _refreshFuture = null;
    }
  }

  static Future<bool> _doRefresh() async {
    final refreshToken = await AuthStorageService.getRefreshToken();
    if (refreshToken == null || refreshToken.isEmpty) {
      return false;
    }
    try {
      final baseUrl = await ApiClient.getBaseUrl();
      final uri = Uri.parse('$baseUrl/api/v1/auth/refresh');
      final resp = await http
          .post(
            uri,
            headers: {'Content-Type': 'application/json', 'Accept': 'application/json'},
            body: jsonEncode({'refresh_token': refreshToken}),
          )
          .timeout(const Duration(seconds: 12));

      if (resp.statusCode == 200) {
        final data = jsonDecode(resp.body) as Map<String, dynamic>;
        await AuthStorageService.saveTokens(
          accessToken: data['access_token'] as String,
          refreshToken: data['refresh_token'] as String,
        );
        return true;
      }
      return false;
    } catch (_) {
      // Network error / offline: do not wipe local session on transient offline state
      return false;
    }
  }

  static Future<void> _handleSessionExpired() async {
    await AuthStorageService.clearAuth();
    final nav = navigatorKey.currentState;
    if (nav != null) {
      nav.pushAndRemoveUntil(
        MaterialPageRoute(builder: (_) => const LoginScreen()),
        (route) => route.isFirst,
      );
    }
  }

  static Future<http.Response> send(
    String method,
    String path, {
    Map<String, String>? headers,
    Object? body,
    Duration timeout = const Duration(seconds: 15),
  }) async {
    final baseUrl = await ApiClient.getBaseUrl();
    final uri = Uri.parse('$baseUrl$path');

    Future<http.Response> execute() async {
      final hdrs = await _buildHeaders(headers);
      switch (method.toUpperCase()) {
        case 'GET':
          return http.get(uri, headers: hdrs).timeout(timeout);
        case 'POST':
          return http.post(uri, headers: hdrs, body: body).timeout(timeout);
        case 'PUT':
          return http.put(uri, headers: hdrs, body: body).timeout(timeout);
        case 'PATCH':
          return http.patch(uri, headers: hdrs, body: body).timeout(timeout);
        case 'DELETE':
          return http.delete(uri, headers: hdrs, body: body).timeout(timeout);
        default:
          throw UnsupportedError('Unsupported HTTP method: $method');
      }
    }

    var resp = await execute();
    if (resp.statusCode == 401) {
      final refreshed = await _refreshTokens();
      if (refreshed) {
        resp = await execute();
      } else {
        await _handleSessionExpired();
      }
    }
    return resp;
  }

  static Future<http.Response> get(String path, {Duration timeout = const Duration(seconds: 15)}) =>
      send('GET', path, timeout: timeout);

  static Future<http.Response> post(String path, {Object? body, Duration timeout = const Duration(seconds: 15)}) =>
      send('POST', path, body: body, timeout: timeout);

  static Future<http.Response> put(String path, {Object? body, Duration timeout = const Duration(seconds: 15)}) =>
      send('PUT', path, body: body, timeout: timeout);

  static Future<http.Response> delete(String path, {Duration timeout = const Duration(seconds: 15)}) =>
      send('DELETE', path, timeout: timeout);
}
