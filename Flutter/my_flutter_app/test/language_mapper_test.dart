import 'package:flutter_test/flutter_test.dart';
import 'package:my_flutter_app/core/language/emergency_language_option.dart';
import 'package:my_flutter_app/core/language/language_mapper.dart';

void main() {
  group('LanguageMapper.toApiCode', () {
    test('maps canonical and locale variants', () {
      expect(LanguageMapper.toApiCode('en'), 'en-IN');
      expect(LanguageMapper.toApiCode('en-US'), 'en-IN');
      expect(LanguageMapper.toApiCode('en_IN'), 'en-IN');
      expect(LanguageMapper.toApiCode('hi-IN'), 'hi-IN');
      expect(LanguageMapper.toApiCode('gu-IN'), 'gu-IN');
      expect(LanguageMapper.toApiCode('mr-IN'), 'mr-IN');
      expect(LanguageMapper.toApiCode('Hindi'), 'hi-IN');
      expect(LanguageMapper.toApiCode('Gujarati'), 'gu-IN');
    });

    test('rejects opaque STT locale IDs', () {
      expect(
        LanguageMapper.toApiCode('MPK-f0gAk-9VDbswqDXFFP1PsMPM2QHMyxM'),
        isNull,
      );
      expect(LanguageMapper.toApiCode('random-token-123'), isNull);
    });
  });

  group('Language selection', () {
    test('api code comes from selection not localeId', () {
      const selected = EmergencyLanguageOption.gujarati;
      expect(LanguageMapper.apiCodeForSelection(selected), 'gu-IN');
      expect(
        LanguageMapper.toApiCode('MPK-f0gAk-9VDbswqDXFFP1PsMPM2QHMyxM'),
        isNull,
      );
    });
  });
}
