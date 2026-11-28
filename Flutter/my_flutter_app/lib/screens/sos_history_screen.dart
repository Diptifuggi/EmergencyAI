import 'package:flutter/material.dart';

import '../l10n/app_localizations.dart';
import '../services/home_feature_api_service.dart';
import 'sos_history_detail_screen.dart';

class SosHistoryScreen extends StatefulWidget {
  const SosHistoryScreen({super.key});

  @override
  State<SosHistoryScreen> createState() => _SosHistoryScreenState();
}

String formatIstTime(String? iso) {
  if (iso == null || iso.isEmpty) return '-';
  final dt = DateTime.tryParse(iso);
  if (dt == null) return iso;
  final ist = dt.toUtc().add(const Duration(hours: 5, minutes: 30));
  String two(int n) => n.toString().padLeft(2, '0');
  return '${two(ist.day)}/${two(ist.month)}/${ist.year} ${two(ist.hour)}:${two(ist.minute)} IST';
}

class _SosHistoryScreenState extends State<SosHistoryScreen> {
  final List<Map<String, dynamic>> _items = [];
  List<Map<String, dynamic>> _reports = [];
  int _selectedTab = 0; // 0 = SOS Alerts, 1 = Voice/Text Reports
  bool _loading = true;
  bool _loadingMore = false;
  int _page = 1;
  int _total = 0;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load(refresh: true);
  }

  Future<void> _load({bool refresh = false}) async {
    if (refresh) {
      setState(() {
        _loading = true;
        _page = 1;
        _error = null;
      });
    } else {
      setState(() => _loadingMore = true);
    }

    try {
      final data = await HomeFeatureApiService.listMySosAlerts(page: _page, pageSize: 20);
      final list = (data['items'] as List<dynamic>).cast<Map<String, dynamic>>();
      List<Map<String, dynamic>> reportList = _reports;
      if (refresh) {
        try {
          final rData = await HomeFeatureApiService.listMyEmergencyCalls(limit: 30);
          reportList = (rData['items'] as List<dynamic>).cast<Map<String, dynamic>>();
        } catch (_) {}
      }
      if (!mounted) return;
      setState(() {
        if (refresh) _items.clear();
        _items.addAll(list);
        _reports = reportList;
        _total = (data['total'] as num?)?.toInt() ?? _items.length;
        _loading = false;
        _loadingMore = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString();
        _loading = false;
        _loadingMore = false;
      });
    }
  }

  Color _typeColor(String type) {
    switch (type) {
      case 'silent_sos':
        return Colors.deepPurple;
      case 'panic_button':
        return Colors.red.shade900;
      default:
        return Colors.red;
    }
  }

  String _typeLabel(String type) {
    switch (type) {
      case 'silent_sos':
        return 'Silent SOS';
      case 'panic_button':
        return 'Panic Button';
      default:
        return 'SOS';
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;

    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.sosHistoryTitle),
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(44),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            child: SegmentedButton<int>(
              segments: const [
                ButtonSegment(value: 0, label: Text('SOS Alerts')),
                ButtonSegment(value: 1, label: Text('Voice / Text Reports')),
              ],
              selected: {_selectedTab},
              onSelectionChanged: (s) => setState(() => _selectedTab = s.first),
            ),
          ),
        ),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(_error!),
                      const SizedBox(height: 12),
                      ElevatedButton(onPressed: () => _load(refresh: true), child: const Text('Retry')),
                    ],
                  ),
                )
              : RefreshIndicator(
                  onRefresh: () => _load(refresh: true),
                  child: _selectedTab == 1
                      ? (_reports.isEmpty
                          ? ListView(
                              children: const [
                                SizedBox(height: 120),
                                Center(child: Text('No voice or text reports sent yet.')),
                              ],
                            )
                          : ListView.builder(
                              padding: const EdgeInsets.all(12),
                              itemCount: _reports.length,
                              itemBuilder: (ctx, i) {
                                final r = _reports[i];
                                final text = (r['text_content'] ?? r['transcription'] ?? 'Voice Report').toString();
                                final status = (r['status'] ?? 'received').toString().toUpperCase();
                                final timeIst = formatIstTime(r['created_at']?.toString());
                                return Card(
                                  margin: const EdgeInsets.only(bottom: 10),
                                  child: ListTile(
                                    leading: const Icon(Icons.assignment_outlined, color: Colors.blue),
                                    title: Text(text, maxLines: 2, overflow: TextOverflow.ellipsis),
                                    subtitle: Text('$timeIst\nStatus: $status'),
                                    isThreeLine: true,
                                  ),
                                );
                              },
                            ))
                      : _items.isEmpty
                      ? ListView(
                          children: [
                            const SizedBox(height: 120),
                            Center(child: Text(l10n.sosHistoryEmpty)),
                          ],
                        )
                      : ListView.builder(
                          padding: const EdgeInsets.all(12),
                          itemCount: _items.length + (_items.length < _total ? 1 : 0),
                          itemBuilder: (ctx, i) {
                            if (i == _items.length) {
                              if (!_loadingMore) {
                                _page++;
                                _load(refresh: false);
                              }
                              return const Padding(
                                padding: EdgeInsets.all(16),
                                child: Center(child: CircularProgressIndicator()),
                              );
                            }

                            final item = _items[i];
                            final type = item['alert_type']?.toString() ?? 'sos';
                            final cat = (item['service_category']?.toString() ?? 'general').toUpperCase();
                            final status = (item['status']?.toString() ?? 'pending').toUpperCase();
                            final formattedTime = formatIstTime(item['received_at']?.toString());

                            return Card(
                              margin: const EdgeInsets.only(bottom: 10),
                              child: ListTile(
                                onTap: () async {
                                  await Navigator.of(context).push(
                                    MaterialPageRoute(
                                      builder: (_) => SosHistoryDetailScreen(alertId: item['id']),
                                    ),
                                  );
                                  _load(refresh: true);
                                },
                                leading: Chip(
                                  backgroundColor: _typeColor(type).withValues(alpha: 0.15),
                                  label: Text(
                                    _typeLabel(type),
                                    style: TextStyle(
                                      color: _typeColor(type),
                                      fontSize: 11,
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                ),
                                title: Text('Service: $cat'),
                                subtitle: Text('$formattedTime\nStatus: $status • Server Received'),
                                isThreeLine: true,
                                trailing: const Icon(Icons.chevron_right),
                              ),
                            );
                          },
                        ),
                ),
    );
  }
}
