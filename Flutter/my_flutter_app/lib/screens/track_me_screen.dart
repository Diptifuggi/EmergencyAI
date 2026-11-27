import 'dart:async';
import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import 'package:share_plus/share_plus.dart';
import 'package:url_launcher/url_launcher.dart';

import '../core/network/api_client.dart';
import '../l10n/app_localizations.dart';
import '../services/home_feature_api_service.dart';
import '../services/sos_location_service.dart';
import '../widgets/app_colors.dart';

class TrackMeScreen extends StatefulWidget {
  const TrackMeScreen({super.key});

  @override
  State<TrackMeScreen> createState() => _TrackMeScreenState();
}

class _TrackMeScreenState extends State<TrackMeScreen> {
  int _selectedHours = 1;
  bool _starting = false;
  bool _stopping = false;
  bool _locationOff = false;

  Map<String, dynamic>? _activeSession;
  Timer? _pointTimer;
  String? _shareUrl;

  @override
  void initState() {
    super.initState();
    _checkLocationStatus();
  }

  @override
  void dispose() {
    _pointTimer?.cancel();
    super.dispose();
  }

  Future<void> _checkLocationStatus() async {
    final perm = await SosLocationService.checkPermission();
    final enabled = await Geolocator.isLocationServiceEnabled();
    if (mounted) {
      setState(() {
        _locationOff = !enabled ||
            perm == LocationPermission.denied ||
            perm == LocationPermission.deniedForever;
      });
    }
  }

  Future<void> _startSession() async {
    setState(() => _starting = true);
    try {
      final fix = await SosLocationService.captureLocation(promptIfDenied: true);
      if (fix.latitude == null || fix.longitude == null) {
        await _checkLocationStatus();
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text(AppLocalizations.of(context)!.locationOffTapToEnable)),
          );
        }
        setState(() => _starting = false);
        return;
      }

      final session = await HomeFeatureApiService.startTrackSession(
        durationHours: _selectedHours,
        latitude: fix.latitude,
        longitude: fix.longitude,
        accuracyM: fix.accuracyM,
      );

      final baseUrl = await ApiClient.getBaseUrl();
      // Construct public dashboard share URL
      final dashboardBase = baseUrl.replaceFirst(':8000', ':5173');
      final url = '$dashboardBase/track/${session['share_token']}';

      if (!mounted) return;
      setState(() {
        _activeSession = session;
        _shareUrl = url;
        _locationOff = false;
        _starting = false;
      });

      _pointTimer?.cancel();
      _pointTimer = Timer.periodic(const Duration(seconds: 20), (_) => _sendPoint());
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
        setState(() => _starting = false);
      }
    }
  }

  Future<void> _sendPoint() async {
    if (_activeSession == null) return;
    try {
      final fix = await SosLocationService.captureLocation(promptIfDenied: false);
      if (fix.latitude != null && fix.longitude != null) {
        await HomeFeatureApiService.sendTrackPoint(
          _activeSession!['id'],
          latitude: fix.latitude!,
          longitude: fix.longitude!,
          accuracyM: fix.accuracyM,
        );
      }
    } catch (_) {}
  }

  Future<void> _stopSession() async {
    if (_activeSession == null) return;
    setState(() => _stopping = true);
    _pointTimer?.cancel();
    try {
      await HomeFeatureApiService.stopTrackSession(_activeSession!['id']);
      if (mounted) {
        setState(() {
          _activeSession = null;
          _shareUrl = null;
          _stopping = false;
        });
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
        setState(() => _stopping = false);
      }
    }
  }

  Future<void> _shareLink() async {
    if (_shareUrl == null) return;
    await Share.share('Track my live location on EmergencyIQ: $_shareUrl');
  }

  Future<void> _shareViaSms() async {
    if (_shareUrl == null) return;
    final uri = Uri(
      scheme: 'sms',
      queryParameters: {'body': 'Track my live location on EmergencyIQ: $_shareUrl'},
    );
    await launchUrl(uri);
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;

    return Scaffold(
      appBar: AppBar(title: Text(l10n.trackMeTitle)),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          if (_locationOff)
            Card(
              color: Colors.amber.withValues(alpha: 0.15),
              child: ListTile(
                leading: const Icon(Icons.location_off, color: Colors.amber),
                title: Text(l10n.locationOffTapToEnable),
                onTap: () async {
                  await SosLocationService.requestPermission();
                  await _checkLocationStatus();
                },
              ),
            ),
          const SizedBox(height: 8),
          if (_activeSession == null) ...[
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Select Sharing Duration',
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 12),
                    Wrap(
                      spacing: 8,
                      children: [1, 2, 4, 8, 12].map((h) {
                        return ChoiceChip(
                          label: Text('$h hr${h > 1 ? 's' : ''}'),
                          selected: _selectedHours == h,
                          onSelected: (_) => setState(() => _selectedHours = h),
                        );
                      }).toList(),
                    ),
                    const SizedBox(height: 16),
                    const Text(
                      'Your GPS location will be updated every 15-30 seconds while active. Only your first name and live position are visible on the shared link.',
                      style: TextStyle(fontSize: 13),
                    ),
                    const SizedBox(height: 16),
                    SizedBox(
                      width: double.infinity,
                      height: 48,
                      child: FilledButton.icon(
                        style: FilledButton.styleFrom(backgroundColor: AppColors.primary),
                        onPressed: _starting ? null : _startSession,
                        icon: const Icon(Icons.my_location),
                        label: Text(_starting ? 'Starting...' : l10n.trackMeStart),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ] else ...[
            Card(
              color: Colors.green.withValues(alpha: 0.08),
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        const Icon(Icons.share_location, color: Colors.green),
                        const SizedBox(width: 8),
                        Text(
                          'Live Session Active ($_selectedHours hr)',
                          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: Colors.green),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text('Expires: ${_activeSession!['expires_at']}'),
                    if (_shareUrl != null) ...[
                      const SizedBox(height: 8),
                      SelectableText(
                        _shareUrl!,
                        style: const TextStyle(fontSize: 12, fontFamily: 'monospace'),
                      ),
                    ],
                    const SizedBox(height: 16),
                    Row(
                      children: [
                        Expanded(
                          child: SizedBox(
                            height: 48,
                            child: OutlinedButton.icon(
                              onPressed: _shareLink,
                              icon: const Icon(Icons.share),
                              label: Text(l10n.trackMeShareLink),
                            ),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: SizedBox(
                            height: 48,
                            child: OutlinedButton.icon(
                              onPressed: _shareViaSms,
                              icon: const Icon(Icons.sms_outlined),
                              label: const Text('SMS'),
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    SizedBox(
                      width: double.infinity,
                      height: 48,
                      child: FilledButton.icon(
                        style: FilledButton.styleFrom(backgroundColor: Colors.red),
                        onPressed: _stopping ? null : _stopSession,
                        icon: const Icon(Icons.stop_circle_outlined),
                        label: Text(_stopping ? 'Stopping...' : l10n.trackMeStop),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}
