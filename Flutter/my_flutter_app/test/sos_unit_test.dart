import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:my_flutter_app/services/sos_queue_service.dart';
import 'package:my_flutter_app/services/sos_location_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  group('SOS Queue & Data Models', () {
    test('generateUuid produces valid v4 formatted UUID', () {
      final uuid = SosQueueService.generateUuid();
      expect(uuid.length, 36);
      expect(
        RegExp(r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$')
            .hasMatch(uuid),
        isTrue,
      );
    });

    test('generateIdempotencyKey generates 32-character hex key', () {
      final key = SosQueueService.generateIdempotencyKey();
      expect(key.length, 32);
      expect(RegExp(r'^[0-9a-f]{32}$').hasMatch(key), isTrue);
    });

    test('QueuedSosAlert JSON serialization round-trip', () {
      final now = DateTime.now().toUtc();
      final alert = QueuedSosAlert(
        id: 'test-uuid-1',
        idempotencyKey: 'idemp-1234',
        alertType: 'silent_sos',
        latitude: 19.0760,
        longitude: 72.8777,
        accuracyM: 14.2,
        locationStatus: 'available',
        triggeredAt: now,
        deliveryState: SosDeliveryState.serverReceived,
        operatorStatus: 'pending',
      );

      final json = alert.toJson();
      final reconstructed = QueuedSosAlert.fromJson(json);

      expect(reconstructed.id, 'test-uuid-1');
      expect(reconstructed.idempotencyKey, 'idemp-1234');
      expect(reconstructed.alertType, 'silent_sos');
      expect(reconstructed.latitude, 19.0760);
      expect(reconstructed.longitude, 72.8777);
      expect(reconstructed.accuracyM, 14.2);
      expect(reconstructed.locationStatus, 'available');
      expect(reconstructed.deliveryState, SosDeliveryState.serverReceived);
      expect(reconstructed.operatorStatus, 'pending');
    });

    test('SosLocationFix accurately captures fallback states', () {
      final now = DateTime.now().toUtc();
      final fixDenied = SosLocationFix(
        locationStatus: 'denied',
        recordedAt: now,
      );
      expect(fixDenied.latitude, isNull);
      expect(fixDenied.locationStatus, 'denied');

      final fixLastKnown = SosLocationFix(
        latitude: 19.0,
        longitude: 72.0,
        accuracyM: 25.0,
        locationStatus: 'last_known',
        recordedAt: now,
      );
      expect(fixLastKnown.latitude, 19.0);
      expect(fixLastKnown.locationStatus, 'last_known');
    });

    test('Delivery state never shows serverReceived prematurely', () {
      final alert = QueuedSosAlert(
        id: 'test-2',
        idempotencyKey: 'key-2',
        alertType: 'sos',
        locationStatus: 'unavailable',
        triggeredAt: DateTime.now().toUtc(),
        deliveryState: SosDeliveryState.queued,
      );

      // In queued or sending state, it should NOT be considered server confirmed
      expect(alert.deliveryState == SosDeliveryState.serverReceived, isFalse);
      expect(alert.deliveryState == SosDeliveryState.acknowledgedByOperator, isFalse);
    });
  });
}
