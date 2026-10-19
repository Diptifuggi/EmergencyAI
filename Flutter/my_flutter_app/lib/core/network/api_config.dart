/// Central API paths and development network defaults for EmergencyIQ.
///
/// Routes: GET health; POST text, voice-text, audio, and STT; GET emergency
/// list; POST map snapshot for an existing emergency.
///
/// Override the backend address at build/run time with:
/// `--dart-define=API_BASE_URL=http://<reachable-host>:8000`.
class ApiConfig {
  ApiConfig._();

  static const String baseUrlOverride =
      String.fromEnvironment('API_BASE_URL', defaultValue: '');
  static const String defaultBaseUrl = 'http://127.0.0.1:8000';
  static const String androidEmulatorBaseUrl = 'http://10.0.2.2:8000';
  static const String adbReverseBaseUrl = 'http://127.0.0.1:8000';

  static const String healthEndpoint = '/api/v1/health';
  static const String emergencyCallsEndpoint = '/api/v1/emergency-calls';
  static const String textEmergencyEndpoint =
      '$emergencyCallsEndpoint/text';
  static const String voiceTextEmergencyEndpoint =
      '$emergencyCallsEndpoint/voice-text';
  static const String audioEmergencyEndpoint = '$emergencyCallsEndpoint/audio';
  static const String sttEndpoint = '/api/v1/stt/transcribe';
  static const String mapSnapshotEndpoint =
      '$emergencyCallsEndpoint/{callId}/map-snapshot';

  static const Duration requestTimeout = Duration(seconds: 30);
  static const Duration uploadTimeout = Duration(seconds: 90);
}
