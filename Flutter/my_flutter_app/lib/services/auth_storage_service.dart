import 'dart:convert';
import 'package:flutter/services.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:shared_preferences/shared_preferences.dart';

class AuthStorageService {
  static const String _keyToken = 'auth_token';
  static const String _keyRefreshToken = 'refresh_token';
  static const String _keyUser = 'user_data';
  static const String _keyProfileDismissed = 'profile_banner_dismissed';

  static const FlutterSecureStorage _secureStorage = FlutterSecureStorage(
    aOptions: AndroidOptions(encryptedSharedPreferences: true),
  );

  static SharedPreferences? _prefs;
  static final Map<String, String> _memoryFallback = {};

  static Future<SharedPreferences> _getPrefs() async {
    _prefs ??= await SharedPreferences.getInstance();
    return _prefs!;
  }

  static Future<void> _writeSecure(String key, String value) async {
    try {
      await _secureStorage.write(key: key, value: value);
    } on MissingPluginException {
      _memoryFallback[key] = value;
    } catch (_) {
      _memoryFallback[key] = value;
    }
  }

  static Future<String?> _readSecure(String key) async {
    try {
      final val = await _secureStorage.read(key: key);
      if (val != null) return val;
    } on MissingPluginException {
      return _memoryFallback[key];
    } catch (_) {}
    return _memoryFallback[key];
  }

  static Future<void> _deleteSecure(String key) async {
    _memoryFallback.remove(key);
    try {
      await _secureStorage.delete(key: key);
    } catch (_) {}
  }

  static Future<void> saveTokens({
    required String accessToken,
    required String refreshToken,
  }) async {
    await _writeSecure(_keyToken, accessToken);
    await _writeSecure(_keyRefreshToken, refreshToken);
    // Remove any legacy plaintext tokens from SharedPreferences
    final prefs = await _getPrefs();
    await prefs.remove(_keyToken);
    await prefs.remove(_keyRefreshToken);
  }

  static Future<String?> getAccessToken() async {
    return _readSecure(_keyToken);
  }

  static Future<String?> getRefreshToken() async {
    return _readSecure(_keyRefreshToken);
  }

  static Future<bool> isLoggedIn() async {
    final access = await getAccessToken();
    final refresh = await getRefreshToken();
    return (access != null && access.isNotEmpty) ||
        (refresh != null && refresh.isNotEmpty);
  }

  static Future<void> saveUserProfile(Map<String, dynamic> userProfile) async {
    final prefs = await _getPrefs();
    await prefs.setString(_keyUser, jsonEncode(userProfile));
  }

  static Future<Map<String, dynamic>?> getUserProfile() async {
    final prefs = await _getPrefs();
    final raw = prefs.getString(_keyUser);
    if (raw == null) return null;
    try {
      return jsonDecode(raw) as Map<String, dynamic>;
    } catch (_) {
      return null;
    }
  }

  static Future<void> setProfileBannerDismissed(bool dismissed) async {
    final prefs = await _getPrefs();
    await prefs.setBool(_keyProfileDismissed, dismissed);
  }

  static Future<bool> isProfileBannerDismissed() async {
    final prefs = await _getPrefs();
    return prefs.getBool(_keyProfileDismissed) ?? false;
  }

  static Future<void> clearAuth() async {
    await _deleteSecure(_keyToken);
    await _deleteSecure(_keyRefreshToken);
    final prefs = await _getPrefs();
    await prefs.remove(_keyToken);
    await prefs.remove(_keyRefreshToken);
    await prefs.remove(_keyUser);
    await prefs.remove(_keyProfileDismissed);
  }
}
