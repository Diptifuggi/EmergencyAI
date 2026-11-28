import 'package:flutter/material.dart';

import 'core/network/api_client.dart';
import 'core/network/auth_http_client.dart';
import 'l10n/app_localizations.dart';
import 'screens/emergency_report_screen.dart';
import 'services/settings_service.dart';
import 'widgets/app_colors.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await ApiClient.init();
  await SettingsService.load();
  runApp(const EmergencyIqApp());
}

class EmergencyIqApp extends StatelessWidget {
  const EmergencyIqApp({super.key});

  @override
  Widget build(BuildContext context) {
    return ValueListenableBuilder<Locale>(
      valueListenable: SettingsService.localeNotifier,
      builder: (context, locale, _) {
        return MaterialApp(
          navigatorKey: AuthHttpClient.navigatorKey,
          title: 'EmergencyIQ',
          debugShowCheckedModeBanner: false,
          locale: locale,
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          supportedLocales: AppLocalizations.supportedLocales,
          theme: ThemeData(
            colorScheme: ColorScheme.fromSeed(seedColor: AppColors.primary),
            useMaterial3: true,
            scaffoldBackgroundColor: AppColors.background,
          ),
          darkTheme: ThemeData(
            colorScheme: ColorScheme.fromSeed(
              seedColor: AppColors.primary,
              brightness: Brightness.dark,
            ),
            useMaterial3: true,
          ),
          home: const EmergencyReportScreen(),
        );
      },
    );
  }
}
