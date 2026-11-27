import 'package:flutter/material.dart';

import '../l10n/app_localizations.dart';
import '../services/home_feature_api_service.dart';

class SosHistoryDetailScreen extends StatefulWidget {
  final String alertId;

  const SosHistoryDetailScreen({super.key, required this.alertId});

  @override
  State<SosHistoryDetailScreen> createState() => _SosHistoryDetailScreenState();
}

class _SosHistoryDetailScreenState extends State<SosHistoryDetailScreen> {
  Map<String, dynamic>? _detail;
  bool _loading = true;
  bool _cancelling = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final data = await HomeFeatureApiService.getMySosDetail(widget.alertId);
      if (!mounted) return;
      setState(() {
        _detail = data;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  Future<void> _cancelAlert() async {
    setState(() => _cancelling = true);
    try {
      await HomeFeatureApiService.cancelSosAlert(widget.alertId);
      await _load();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('SOS alert cancelled')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
      }
    } finally {
      if (mounted) setState(() => _cancelling = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;

    return Scaffold(
      appBar: AppBar(title: Text(l10n.sosHistoryTitle)),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null || _detail == null
              ? Center(child: Text(_error ?? 'Not found'))
              : ListView(
                  padding: const EdgeInsets.all(16),
                  children: [
                    Card(
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Status: ${(_detail!['status'] ?? '').toString().toUpperCase()}',
                              style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
                            ),
                            const SizedBox(height: 6),
                            Text('Type: ${_detail!['alert_type']}'),
                            Text('Service: ${(_detail!['service_category'] ?? 'general').toString().toUpperCase()}'),
                            Text(
                              'Location Accuracy: ${_detail!['accuracy_m'] != null ? '±${(_detail!['accuracy_m'] as num).round()} m' : _detail!['location_status']}',
                            ),
                            if (_detail!['acknowledged_at'] != null)
                              Text('Operator Acknowledged At: ${_detail!['acknowledged_at']}'),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 16),
                    if (_detail!['status'] == 'pending')
                      SizedBox(
                        height: 48,
                        child: FilledButton.icon(
                          style: FilledButton.styleFrom(backgroundColor: Colors.red),
                          onPressed: _cancelling ? null : _cancelAlert,
                          icon: const Icon(Icons.cancel),
                          label: Text(_cancelling ? 'Cancelling...' : l10n.cancelBtn),
                        ),
                      ),
                    const SizedBox(height: 20),
                    Text(
                      'Status Timeline',
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 8),
                    ...((_detail!['events'] as List<dynamic>? ?? []).map((evt) {
                      final m = evt as Map<String, dynamic>;
                      return ListTile(
                        leading: const Icon(Icons.timeline, size: 20),
                        title: Text((m['event_type'] ?? '').toString().replaceAll('_', ' ').toUpperCase()),
                        subtitle: Text('${m['actor_type']} • ${m['created_at'] ?? ''}'),
                      );
                    })),
                  ],
                ),
    );
  }
}
