import 'package:speech_to_text/speech_to_text.dart';

import 'emergency_language_option.dart';

/// Converts UI/STT representations into canonical EmergencyIQ API language codes.
class LanguageMapper {
  LanguageMapper._();

  static const Set<String> validApiCodes = {'en', 'hi', 'gu', 'mr'};

  /// Returns canonical API code or null if [raw] cannot be resolved safely.
  ///
  /// Opaque STT identifiers such as `MPK-f0gAk-...` are intentionally rejected.
  static String? toApiCode(String? raw) {
    if (raw == null) return null;
    final trimmed = raw.trim();
    if (trimmed.isEmpty) return null;

    final normalized = trimmed.toLowerCase().replaceAll('_', '-');
    if (validApiCodes.contains(normalized)) {
      return normalized;
    }

    final primary = normalized.split('-').first;
    if (validApiCodes.contains(primary)) {
      return primary;
    }

    for (final option in EmergencyLanguageOption.all) {
      if (normalized == option.displayName.toLowerCase()) {
        return option.apiCode;
      }
    }

    // Reject opaque engine locale IDs and other unknown tokens.
    if (_looksLikeOpaqueLocaleId(trimmed)) {
      return null;
    }

    return null;
  }

  /// Canonical API code from the user's selected language.
  static String apiCodeForSelection(EmergencyLanguageOption selected) {
    return selected.apiCode;
  }

  static bool isValidApiCode(String? code) {
    return code != null && validApiCodes.contains(code.trim().toLowerCase());
  }

  /// Resolve API code using selected language first, then optional raw fallback.
  static String? resolveApiCode({
    required EmergencyLanguageOption selected,
    String? rawFallback,
  }) {
    final fromSelection = apiCodeForSelection(selected);
    if (isValidApiCode(fromSelection)) {
      return fromSelection;
    }
    return toApiCode(rawFallback);
  }

  /// Pick the best STT locale for the selected language from device locales.
  static LocaleName? pickSttLocale(
    List<LocaleName> locales,
    EmergencyLanguageOption selected,
  ) {
    if (locales.isEmpty) return null;

    bool matches(LocaleName locale) {
      final localeId = locale.localeId.toLowerCase();
      final localeName = locale.name.toLowerCase();
      for (final prefix in selected.sttLocalePrefixes) {
        final p = prefix.toLowerCase();
        if (localeId == p ||
            localeId.startsWith('$p-') ||
            localeId.startsWith('${p}_') ||
            localeName.contains(selected.displayName.toLowerCase())) {
          return true;
        }
      }
      return false;
    }

    final preferred = locales.where(matches).toList();
    if (preferred.isEmpty) return null;

    preferred.sort((a, b) {
      int score(LocaleName locale) {
        final id = locale.localeId.toLowerCase();
        if (id.contains('_in') || id.contains('-in')) return 0;
        if (id.startsWith(selected.apiCode)) return 1;
        return 2;
      }

      return score(a).compareTo(score(b));
    });

    return preferred.first;
  }

  static bool _looksLikeOpaqueLocaleId(String value) {
    // Android speech engine IDs (e.g. MPK-f0gAk-9VDbswqDXFFP1PsMPM2QHMyxM)
    // must never be sent as EmergencyIQ API language codes.
    if (value.contains('-') && !value.contains('_')) {
      final parts = value.split('-');
      if (parts.length >= 2 && parts.first.length >= 3) {
        final first = parts.first.toLowerCase();
        if (!validApiCodes.contains(first) &&
            !{'en', 'hi', 'gu', 'mr'}.contains(first)) {
          return RegExp(r'^[a-z]{2,3}$', caseSensitive: false).hasMatch(parts.first) ==
              false;
        }
      }
    }
    return value.startsWith('MPK-') || value.length > 12;
  }
}
