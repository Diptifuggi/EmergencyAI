import 'emergency_language_option.dart';

/// Converts UI/STT representations into canonical EmergencyIQ API language codes.
class LanguageMapper {
  LanguageMapper._();

  static const Set<String> validApiCodes = {
    'auto', 'en-IN', 'hi-IN', 'gu-IN', 'mr-IN'
  };

  /// Returns canonical API code or null if [raw] cannot be resolved safely.
  ///
  /// Opaque STT identifiers such as `MPK-f0gAk-...` are intentionally rejected.
  static String? toApiCode(String? raw) {
    if (raw == null) return null;
    final trimmed = raw.trim();
    if (trimmed.isEmpty) return null;

    final normalized = trimmed.replaceAll('_', '-');
    final lower = normalized.toLowerCase();
    const primaryToBcp47 = {
      'en': 'en-IN', 'hi': 'hi-IN', 'gu': 'gu-IN', 'mr': 'mr-IN',
    };
    if (lower == 'auto') return 'auto';
    if (primaryToBcp47.containsKey(lower)) return primaryToBcp47[lower];
    if (primaryToBcp47.containsKey(lower.split('-').first)) {
      return primaryToBcp47[lower.split('-').first];
    }
    if (validApiCodes.contains(normalized)) {
      return normalized;
    }

    final primary = normalized.split('-').first;
    if (validApiCodes.contains(primary)) {
      return primary;
    }

    for (final option in EmergencyLanguageOption.all) {
      if (lower == option.displayName.toLowerCase()) {
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
    return code != null &&
      validApiCodes.contains(code.trim() == 'auto'
        ? 'auto'
        : code.trim().replaceAll('_', '-'));
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
