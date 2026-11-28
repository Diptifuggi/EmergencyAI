import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:share_plus/share_plus.dart';
import 'package:url_launcher/url_launcher.dart';

import '../l10n/app_localizations.dart';
import '../services/sos_location_service.dart';
import '../services/track_me_service.dart';
import '../widgets/app_colors.dart';

class TrackMeScreen extends StatefulWidget {
  const TrackMeScreen({super.key});

  @override
  State<TrackMeScreen> createState() => _TrackMeScreenState();
}

class _TrackMeScreenState extends State<TrackMeScreen> {
  final TrackMeService _trackService = TrackMeService();
  int _selectedHours = 1;
  bool _shareWithControlRoom = false;
  bool _starting = false;
  bool _stopping = false;
  bool _locationOff = false;

  @override
  void initState() {
    super.initState();
    _trackService.init();
    _checkLocationStatus();
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

  Future<void> _requestPermissions() async {
    await SosLocationService.requestPermission();
    try {
      await Permission.notification.request();
    } catch (_) {}
    await _checkLocationStatus();
  }

  Future<void> _startSession() async {
    setState(() => _starting = true);
    try {
      try {
        await Permission.notification.request();
      } catch (_) {}

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

      await _trackService.startSession(
        durationHours: _selectedHours,
        shareWithControlRoom: _shareWithControlRoom,
        latitude: fix.latitude!,
        longitude: fix.longitude!,
        accuracyM: fix.accuracyM,
      );

      if (mounted) {
        setState(() {
          _locationOff = false;
          _starting = false;
        });
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
        setState(() => _starting = false);
      }
    }
  }

  Future<void> _stopSession() async {
    setState(() => _stopping = true);
    await _trackService.stopSession();
    if (mounted) setState(() => _stopping = false);
  }

  Future<void> _shareLink() async {
    final url = _trackService.shareUrl;
    if (url == null) return;
    await Share.share('Track my live location on EmergencyIQ: $url');
  }

  Future<void> _shareViaSms() async {
    final url = _trackService.shareUrl;
    if (url == null) return;
    final uri = Uri(
      scheme: 'sms',
      queryParameters: {'body': 'Track my live location on EmergencyIQ: $url'},
    );
    await launchUrl(uri);
  }

  String _stateLabel(TrackMeState s, int queued) {
    switch (s) {
      case TrackMeState.active:
        return 'ACTIVE • Sharing live GPS';
      case TrackMeState.stale:
        return 'STALE • Waiting for GPS fix';
      case TrackMeState.offlineQueued:
        return 'OFFLINE QUEUED • $queued point(s) buffered';
      case TrackMeState.ended:
        return 'SESSION ENDED';
      case TrackMeState.idle:
        return 'READY';
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;

    return Scaffold(
      appBar: AppBar(title: Text(l10n.trackMeTitle)),
      body: ValueListenableBuilder<TrackMeState>(
        valueListenable: _trackService.stateNotifier,
        builder: (context, trackState, _) {
          final session = _trackService.activeSession;
          final shareUrl = _trackService.shareUrl;
          return ValueListenableBuilder<int>(
            valueListenable: _trackService.queuedCountNotifier,
            builder: (context, queuedCount, _) {
              return ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  if (_locationOff)
                    Card(
                      color: Colors.amber.withValues(alpha: 0.15),
                      child: ListTile(
                        leading: const Icon(Icons.location_off, color: Colors.amber),
                        title: Text(l10n.locationOffTapToEnable),
                        onTap: _requestPermissions,
                      ),
                    ),
                  const SizedBox(height: 8),
                  if (session == null) ...[
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
                            const SizedBox(height: 12),
                            SwitchListTile(
                              contentPadding: EdgeInsets.zero,
                              title: const Text('Share with control room'),
                              subtitle: const Text(
                                'Allow EmergencyIQ operators to view this live session on the dispatch map',
                                style: TextStyle(fontSize: 12),
                              ),
                              value: _shareWithControlRoom,
                              onChanged: (v) => setState(() => _shareWithControlRoom = v),
                            ),
                            const SizedBox(height: 12),
                            const Text(
                              'Your GPS location updates every 15-30s (battery-aware) and buffers offline if signal drops.',
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
                      color: trackState == TrackMeState.offlineQueued
                          ? Colors.orange.withValues(alpha: 0.08)
                          : Colors.green.withValues(alpha: 0.08),
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                Icon(
                                  Icons.share_location,
                                  color: trackState == TrackMeState.offlineQueued
                                      ? Colors.orange
                                      : Colors.green,
                                ),
                                const SizedBox(width: 8),
                                Expanded(
                                  child: Text(
                                    _stateLabel(trackState, queuedCount),
                                    style: TextStyle(
                                      fontWeight: FontWeight.bold,
                                      fontSize: 14,
                                      color: trackState == TrackMeState.offlineQueued
                                          ? Colors.orange
                                          : Colors.green,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 8),
                            Text('Expires: ${session['expires_at']}'),
                            if (shareUrl != null) ...[
                              const SizedBox(height: 8),
                              SelectableText(
                                shareUrl,
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
              );
            },
          );
        },
      ),
    );
  }
}
