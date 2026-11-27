import 'package:flutter/material.dart';
import 'package:permission_handler/permission_handler.dart';

import '../l10n/app_localizations.dart';
import '../services/settings_service.dart';
import '../services/sos_queue_service.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  AppSettings _settings = const AppSettings();
  PermissionStatus _locStatus = PermissionStatus.denied;
  PermissionStatus _micStatus = PermissionStatus.denied;

  @override
  void initState() {
    super.initState();
    _loadAll();
  }

  Future<void> _loadAll() async {
    final s = await SettingsService.load();
    PermissionStatus loc = PermissionStatus.denied;
    PermissionStatus mic = PermissionStatus.denied;
    try {
      loc = await Permission.location.status;
      mic = await Permission.microphone.status;
    } catch (_) {}

    if (mounted) {
      setState(() {
        _settings = s;
        _locStatus = loc;
        _micStatus = mic;
      });
    }
  }

  Future<void> _update(AppSettings next) async {
    setState(() => _settings = next);
    await SettingsService.save(next);
  }

  Future<void> _clearOfflineQueue() async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Clear Offline Queue?'),
        content: const Text('This removes all pending unsent SOS items stored locally.'),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Cancel')),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: Colors.red),
            onPressed: () => Navigator.of(ctx).pop(true),
            child: const Text('Clear'),
          ),
        ],
      ),
    );
    if (confirm == true) {
      await SosQueueService().clearQueue();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Offline SOS queue cleared')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;

    return Scaffold(
      appBar: AppBar(title: Text(l10n.settingsTitle)),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          ListTile(
            leading: const Icon(Icons.language),
            title: const Text('App Language'),
            trailing: DropdownButton<String>(
              value: _settings.languageCode,
              items: const [
                DropdownMenuItem(value: 'en', child: Text('English')),
                DropdownMenuItem(value: 'hi', child: Text('हिन्दी (Hindi)')),
                DropdownMenuItem(value: 'gu', child: Text('ગુજરાતી (Gujarati)')),
                DropdownMenuItem(value: 'mr', child: Text('मराठी (Marathi)')),
              ],
              onChanged: (val) {
                if (val != null) {
                  _update(_settings.copyWith(languageCode: val));
                }
              },
            ),
          ),
          const Divider(),
          ListTile(
            leading: const Icon(Icons.timer_outlined),
            title: Text('Cancel Countdown (${_settings.cancelCountdownSeconds}s)'),
            subtitle: Slider(
              min: 3,
              max: 10,
              divisions: 7,
              value: _settings.cancelCountdownSeconds.toDouble(),
              label: '${_settings.cancelCountdownSeconds}s',
              onChanged: (v) => _update(_settings.copyWith(cancelCountdownSeconds: v.round())),
            ),
          ),
          SwitchListTile(
            secondary: const Icon(Icons.vibration),
            title: const Text('Vibration Feedback'),
            value: _settings.vibrationEnabled,
            onChanged: (v) => _update(_settings.copyWith(vibrationEnabled: v)),
          ),
          SwitchListTile(
            secondary: const Icon(Icons.volume_off),
            title: const Text('Silent Mode Default for Emergency Tile'),
            value: _settings.silentModeDefault,
            onChanged: (v) => _update(_settings.copyWith(silentModeDefault: v)),
          ),
          SwitchListTile(
            secondary: const Icon(Icons.location_on_outlined),
            title: const Text('Live Location Sharing During Active SOS'),
            value: _settings.liveLocationEnabled,
            onChanged: (v) => _update(_settings.copyWith(liveLocationEnabled: v)),
          ),
          const Divider(),
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 8),
            child: Text('Permissions', style: TextStyle(fontWeight: FontWeight.bold)),
          ),
          ListTile(
            leading: Icon(
              Icons.my_location,
              color: _locStatus.isGranted ? Colors.green : Colors.orange,
            ),
            title: const Text('Location Permission'),
            subtitle: Text(_locStatus.name),
            trailing: TextButton(
              onPressed: openAppSettings,
              child: const Text('Open settings'),
            ),
          ),
          ListTile(
            leading: Icon(
              Icons.mic,
              color: _micStatus.isGranted ? Colors.green : Colors.orange,
            ),
            title: const Text('Microphone Permission'),
            subtitle: Text(_micStatus.name),
            trailing: TextButton(
              onPressed: openAppSettings,
              child: const Text('Open settings'),
            ),
          ),
          const Divider(),
          const SizedBox(height: 8),
          SizedBox(
            height: 48,
            child: OutlinedButton.icon(
              style: OutlinedButton.styleFrom(foregroundColor: Colors.red),
              onPressed: _clearOfflineQueue,
              icon: const Icon(Icons.delete_sweep_outlined),
              label: const Text('Clear offline queue'),
            ),
          ),
        ],
      ),
    );
  }
}
