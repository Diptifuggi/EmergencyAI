/// Supported EmergencyIQ languages for UI selection, STT, and backend API.
class EmergencyLanguageOption {
  const EmergencyLanguageOption({
    required this.displayName,
    required this.apiCode,
    required this.sttLocalePrefixes,
  });

  final String displayName;
  final String apiCode;

  /// Prefixes used to match speech_to_text [LocaleName.localeId] values.
  final List<String> sttLocalePrefixes;

  static const english = EmergencyLanguageOption(
    displayName: 'English',
    apiCode: 'en',
    sttLocalePrefixes: ['en'],
  );

  static const hindi = EmergencyLanguageOption(
    displayName: 'Hindi',
    apiCode: 'hi',
    sttLocalePrefixes: ['hi'],
  );

  static const gujarati = EmergencyLanguageOption(
    displayName: 'Gujarati',
    apiCode: 'gu',
    sttLocalePrefixes: ['gu'],
  );

  static const marathi = EmergencyLanguageOption(
    displayName: 'Marathi',
    apiCode: 'mr',
    sttLocalePrefixes: ['mr'],
  );

  static const List<EmergencyLanguageOption> all = [
    english,
    hindi,
    gujarati,
    marathi,
  ];

  static EmergencyLanguageOption? fromApiCode(String? code) {
    if (code == null) return null;
    final normalized = code.trim().toLowerCase();
    for (final option in all) {
      if (option.apiCode == normalized) {
        return option;
      }
    }
    return null;
  }
}
