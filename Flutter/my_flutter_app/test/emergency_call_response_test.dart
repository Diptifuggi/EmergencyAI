import 'package:flutter_test/flutter_test.dart';
import 'package:my_flutter_app/core/network/api_config.dart';
import 'package:my_flutter_app/models/emergency_call.dart';

void main() {
  test('API paths match the versioned FastAPI routes', () {
    expect(ApiConfig.healthEndpoint, '/api/v1/health');
    expect(ApiConfig.textEmergencyEndpoint, '/api/v1/emergency-calls/text');
    expect(ApiConfig.sttEndpoint, '/api/v1/stt/transcribe');
  });

  test('emergency response accepts missing nullable fields and preserves extras', () {
    final call = EmergencyCall.fromJson({
      'id': 'emergency-123',
      'call_type': 'text',
      'text_content': 'Need help',
      'status': 'received',
      'priority': 'high',
      'location_status': 'unavailable',
      'analysis_summary': 'Backend-provided analysis',
    });

    expect(call.id, 'emergency-123');
    expect(call.textContent, 'Need help');
    expect(call.latitude, isNull);
    expect(call.locationAccuracy, isNull);
    expect(call.rawJson['analysis_summary'], 'Backend-provided analysis');
  });

}
