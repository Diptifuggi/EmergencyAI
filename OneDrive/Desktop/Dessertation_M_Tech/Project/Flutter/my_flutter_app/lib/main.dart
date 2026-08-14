import 'package:flutter/material.dart';

import 'core/network/api_client.dart';
import 'screens/emergency_report_screen.dart';
import 'widgets/app_colors.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await ApiClient.init();
  runApp(const EmergencyIqApp());
}

class EmergencyIqApp extends StatelessWidget {
  const EmergencyIqApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'EmergencyIQ',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: AppColors.primary),
        useMaterial3: true,
        scaffoldBackgroundColor: AppColors.background,
      ),
      home: const EmergencyReportScreen(),
    );
  }
}
