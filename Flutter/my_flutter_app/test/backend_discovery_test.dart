import 'package:flutter_test/flutter_test.dart';
import 'package:my_flutter_app/core/network/backend_discovery.dart';

void main() {
  group('BackendDiscovery', () {
    test('normalizeBaseUrl adds scheme and trims trailing slash', () {
      expect(
        BackendDiscovery.normalizeBaseUrl('192.168.1.10:8000/'),
        'http://192.168.1.10:8000',
      );
      expect(
        BackendDiscovery.normalizeBaseUrl('http://127.0.0.1:8000'),
        'http://127.0.0.1:8000',
      );
    });

    test('candidateBackends prefers adb reverse then Android emulator host', () {
      final candidates = BackendDiscovery.candidateBackends();
      expect(candidates, [
        'http://127.0.0.1:8000',
        'http://10.0.2.2:8000',
      ]);
    });

    test('selectHealthyBackend picks the first healthy candidate', () async {
      final selected = await BackendDiscovery.selectHealthyBackend(
        candidates: [
          'http://127.0.0.1:8000',
          'http://10.0.2.2:8000',
        ],
        probe: (candidate) async => candidate == 'http://10.0.2.2:8000',
      );

      expect(selected, 'http://10.0.2.2:8000');
    });

    test('selectHealthyBackend returns null when every candidate fails', () async {
      final selected = await BackendDiscovery.selectHealthyBackend(
        candidates: [
          'http://127.0.0.1:8000',
          'http://10.0.2.2:8000',
        ],
        probe: (_) async => false,
      );

      expect(selected, isNull);
    });

    test('prioritizedHosts scans gateway and common dev IPs first', () {
      final hosts = BackendDiscovery.prioritizedHosts();
      expect(hosts.first, 1);
      expect(hosts, contains(254));
      expect(hosts.length, 254);
    });
  });
}
