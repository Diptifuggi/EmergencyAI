import 'package:flutter/material.dart';

import '../l10n/app_localizations.dart';
import '../widgets/app_colors.dart';

class AboutUsScreen extends StatelessWidget {
  const AboutUsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;

    return Scaffold(
      appBar: AppBar(title: Text(l10n.aboutUsTitle)),
      body: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Icon(Icons.emergency_share, size: 56, color: AppColors.primary),
            const SizedBox(height: 16),
            Text(
              l10n.appTitle,
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 12),
            const Text(
              'EmergencyIQ is an integrated emergency assistance and triage platform designed to help citizens request immediate aid through voice, text, or one-tap SOS alerts with live GPS sharing.',
              style: TextStyle(fontSize: 15, height: 1.5),
            ),
            const SizedBox(height: 16),
            const Text(
              'Our mission is to reduce response time and provide dispatchers with accurate, consented safety information when every second counts.',
              style: TextStyle(fontSize: 15, height: 1.5),
            ),
          ],
        ),
      ),
    );
  }
}
