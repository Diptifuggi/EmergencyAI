import 'package:flutter_test/flutter_test.dart';
import 'package:my_flutter_app/core/language/emergency_language_option.dart';
import 'package:my_flutter_app/core/language/language_mapper.dart';
import 'package:speech_to_text/speech_to_text.dart';

void main() {
  group('LanguageMapper.toApiCode', () {
    test('maps canonical and locale variants', () {
      expect(LanguageMapper.toApiCode('en'), 'en');
      expect(LanguageMapper.toApiCode('en-US'), 'en');
      expect(LanguageMapper.toApiCode('en_IN'), 'en');
      expect(LanguageMapper.toApiCode('hi-IN'), 'hi');
      expect(LanguageMapper.toApiCode('gu-IN'), 'gu');
      expect(LanguageMapper.toApiCode('mr-IN'), 'mr');
      expect(LanguageMapper.toApiCode('Hindi'), 'hi');
      expect(LanguageMapper.toApiCode('Gujarati'), 'gu');
    });

    test('rejects opaque STT locale IDs', () {
      expect(
        LanguageMapper.toApiCode('MPK-f0gAk-9VDbswqDXFFP1PsMPM2QHMyxM'),
        isNull,
      );
      expect(LanguageMapper.toApiCode('random-token-123'), isNull);
    });
  });

  group('LanguageMapper.pickSttLocale', () {
    test('prefers India locale for Gujarati', () {
      final locales = [
        LocaleName('MPK-f0gAk-9VDbswqDXFFP1PsMPM2QHMyxM', 'Gujarati (India)'),
        LocaleName('en_US', 'English (United States)'),
      ];

      final picked = LanguageMapper.pickSttLocale(
        locales,
        EmergencyLanguageOption.gujarati,
      );

      expect(picked?.localeId, 'MPK-f0gAk-9VDbswqDXFFP1PsMPM2QHMyxM');
    });

    test('api code comes from selection not localeId', () {
      const selected = EmergencyLanguageOption.gujarati;
      expect(LanguageMapper.apiCodeForSelection(selected), 'gu');
      expect(
        LanguageMapper.toApiCode('MPK-f0gAk-9VDbswqDXFFP1PsMPM2QHMyxM'),
        isNull,
      );
    });
  });
}
