import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:my_flutter_app/core/constants/emergency_services.dart';
import 'package:my_flutter_app/l10n/app_localizations.dart';
import 'package:my_flutter_app/screens/emergency_report_screen.dart';
import 'package:my_flutter_app/screens/e_contact_screen.dart';
import 'package:my_flutter_app/screens/sos_history_screen.dart';
import 'package:my_flutter_app/screens/track_me_screen.dart';
import 'package:my_flutter_app/services/settings_service.dart';
import 'package:my_flutter_app/widgets/emergency_drawer.dart';
import 'package:my_flutter_app/widgets/service_sos_bottom_sheet.dart';

Widget _wrapWithL10n(Widget child, {Locale locale = const Locale('en')}) {
  return MaterialApp(
    locale: locale,
    localizationsDelegates: AppLocalizations.localizationsDelegates,
    supportedLocales: AppLocalizations.supportedLocales,
    home: child,
  );
}

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets('Home screen renders 8 shortcut tiles and 8 service tiles', (tester) async {
    await tester.pumpWidget(_wrapWithL10n(const EmergencyReportScreen()));
    await tester.pump();

    // 8 shortcuts
    expect(find.text('Profile'), findsOneWidget);
    expect(find.text('SOS History'), findsOneWidget);
    expect(find.text('Notification'), findsOneWidget);
    expect(find.text('About Us'), findsOneWidget);
    expect(find.text('Dial 112'), findsOneWidget);
    expect(find.text('Chat Us'), findsOneWidget);
    expect(find.text('TrackMe'), findsOneWidget);
    expect(find.text('Emergency'), findsOneWidget);

    // 8 emergency services
    expect(find.text('Police'), findsOneWidget);
    expect(find.text('Fire'), findsOneWidget);
    expect(find.text('Medical'), findsOneWidget);
    expect(find.text('Disaster'), findsOneWidget);
    expect(find.text('Woman'), findsOneWidget);
    expect(find.text('Child'), findsOneWidget);
    expect(find.text('Elderly'), findsOneWidget);
    expect(find.text('Railway'), findsOneWidget);
  });

  testWidgets('Drawer renders all required menu items', (tester) async {
    await tester.pumpWidget(
      _wrapWithL10n(
        const Scaffold(
          drawer: EmergencyDrawer(),
          body: SizedBox.shrink(),
        ),
      ),
    );
    await tester.pump();

    final ScaffoldState state = tester.firstState(find.byType(Scaffold));
    state.openDrawer();
    await tester.pumpAndSettle();

    expect(find.text('Home'), findsOneWidget);
    expect(find.text('Profile'), findsOneWidget);
    expect(find.text('E-Contact'), findsOneWidget);
    expect(find.text('SOS History'), findsOneWidget);
    expect(find.text('Settings'), findsOneWidget);
    expect(find.text('App Info'), findsOneWidget);
    expect(find.text('Top Questions'), findsOneWidget);
    await tester.scrollUntilVisible(
      find.text('Logout'),
      100,
      scrollable: find.descendant(of: find.byType(Drawer), matching: find.byType(Scrollable)),
    );
    expect(find.text('Logout'), findsOneWidget);
  });

  testWidgets('Service SOS Bottom Sheet renders service label and dial button', (tester) async {
    final fireService = EmergencyServicesConstants.services.firstWhere((s) => s.key == 'fire');
    await tester.pumpWidget(
      _wrapWithL10n(
        Scaffold(
          body: ServiceSosBottomSheet(service: fireService, serviceLabel: 'Fire'),
        ),
      ),
    );
    await tester.pump();

    expect(find.text('Send Fire SOS'), findsOneWidget);
    expect(find.text('Call 101'), findsOneWidget);
    expect(find.text('Hold 2s to Send SOS'), findsOneWidget);
    expect(find.text('Cancel'), findsOneWidget);
  });

  testWidgets('E-Contact, SOS History, and TrackMe screens mount cleanly', (tester) async {
    await tester.pumpWidget(_wrapWithL10n(const EContactScreen()));
    await tester.pump();
    expect(find.text('Emergency Contacts'), findsOneWidget);

    await tester.pumpWidget(_wrapWithL10n(const SosHistoryScreen()));
    await tester.pump();
    expect(find.text('SOS History'), findsOneWidget);

    await tester.pumpWidget(_wrapWithL10n(const TrackMeScreen()));
    await tester.pump();
    expect(find.text('TrackMe Live Sharing'), findsOneWidget);
    expect(find.text('Start TrackMe'), findsOneWidget);
  });

  test('SettingsService switches locale notifier cleanly', () async {
    await SettingsService.setLanguage('hi');
    expect(SettingsService.localeNotifier.value.languageCode, 'hi');
    await SettingsService.setLanguage('en');
    expect(SettingsService.localeNotifier.value.languageCode, 'en');
  });
}
