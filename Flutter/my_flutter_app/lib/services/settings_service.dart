import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

class AppSettings {
  final String languageCode;
  final int cancelCountdownSeconds;
  final bool vibrationEnabled;
  final bool silentModeDefault;
  final bool liveLocationEnabled;

  const AppSettings({
    this.languageCode = 'en',
    this.cancelCountdownSeconds = 5,
    this.vibrationEnabled = true,
    this.silentModeDefault = false,
    this.liveLocationEnabled = true,
  });

  AppSettings copyWith({
    String? languageCode,
    int? cancelCountdownSeconds,
    bool? vibrationEnabled,
    bool? silentModeDefault,
    bool? liveLocationEnabled,
  }) {
    return AppSettings(
      languageCode: languageCode ?? this.languageCode,
      cancelCountdownSeconds: cancelCountdownSeconds ?? this.cancelCountdownSeconds,
      vibrationEnabled: vibrationEnabled ?? this.vibrationEnabled,
      silentModeDefault: silentModeDefault ?? this.silentModeDefault,
      liveLocationEnabled: liveLocationEnabled ?? this.liveLocationEnabled,
    );
  }
}

class SettingsService {
  static const _langKey = 'app_language_code';
  static const _countdownKey = 'sos_cancel_countdown_sec';
  static const _vibrationKey = 'sos_vibration_enabled';
  static const _silentDefaultKey = 'sos_silent_default';
  static const _liveLocKey = 'sos_live_location_enabled';

  static final ValueNotifier<Locale> localeNotifier = ValueNotifier(const Locale('en'));

  static Future<AppSettings> load() async {
    final prefs = await SharedPreferences.getInstance();
    final lang = prefs.getString(_langKey) ?? 'en';
    localeNotifier.value = Locale(lang);
    return AppSettings(
      languageCode: lang,
      cancelCountdownSeconds: (prefs.getInt(_countdownKey) ?? 5).clamp(3, 10),
      vibrationEnabled: prefs.getBool(_vibrationKey) ?? true,
      silentModeDefault: prefs.getBool(_silentDefaultKey) ?? false,
      liveLocationEnabled: prefs.getBool(_liveLocKey) ?? true,
    );
  }

  static Future<void> save(AppSettings settings) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_langKey, settings.languageCode);
    await prefs.setInt(_countdownKey, settings.cancelCountdownSeconds.clamp(3, 10));
    await prefs.setBool(_vibrationKey, settings.vibrationEnabled);
    await prefs.setBool(_silentDefaultKey, settings.silentModeDefault);
    await prefs.setBool(_liveLocKey, settings.liveLocationEnabled);
    localeNotifier.value = Locale(settings.languageCode);
  }

  static Future<void> setLanguage(String code) async {
    final current = await load();
    await save(current.copyWith(languageCode: code));
  }
}
