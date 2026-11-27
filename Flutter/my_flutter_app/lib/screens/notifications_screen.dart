import 'dart:async';
import 'package:flutter/material.dart';

import '../l10n/app_localizations.dart';
import '../services/home_feature_api_service.dart';

class NotificationsScreen extends StatefulWidget {
  const NotificationsScreen({super.key});

  @override
  State<NotificationsScreen> createState() => _NotificationsScreenState();
}

class _NotificationsScreenState extends State<NotificationsScreen> {
  List<Map<String, dynamic>> _items = [];
  bool _loading = true;
  Timer? _pollTimer;

  @override
  void initState() {
    super.initState();
    _load();
    _pollTimer = Timer.periodic(const Duration(seconds: 15), (_) => _load(silent: true));
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    super.dispose();
  }

  Future<void> _load({bool silent = false}) async {
    if (!silent) setState(() => _loading = true);
    try {
      final data = await HomeFeatureApiService.listNotifications();
      final list = (data['items'] as List<dynamic>).cast<Map<String, dynamic>>();
      if (mounted) {
        setState(() {
          _items = list;
          _loading = false;
        });
      }
    } catch (_) {
      if (mounted && !silent) setState(() => _loading = false);
    }
  }

  Future<void> _markRead(String id) async {
    await HomeFeatureApiService.markNotificationRead(id);
    await _load(silent: true);
  }

  Future<void> _markAllRead() async {
    await HomeFeatureApiService.markAllNotificationsRead();
    await _load(silent: true);
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;

    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.notificationsTitle),
        actions: [
          TextButton(
            onPressed: _items.isEmpty ? null : _markAllRead,
            child: Text(l10n.markAllRead),
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _load,
              child: _items.isEmpty
                  ? ListView(
                      children: [
                        const SizedBox(height: 120),
                        Center(child: Text(l10n.notificationsEmpty)),
                      ],
                    )
                  : ListView.builder(
                      itemCount: _items.length,
                      itemBuilder: (ctx, i) {
                        final item = _items[i];
                        final isRead = item['is_read'] == true;
                        return ListTile(
                          tileColor: isRead ? null : Theme.of(context).colorScheme.primary.withValues(alpha: 0.06),
                          leading: Icon(
                            isRead ? Icons.notifications_none : Icons.notifications_active,
                            color: isRead ? Colors.grey : Theme.of(context).colorScheme.primary,
                          ),
                          title: Text(
                            item['title'] ?? '',
                            style: TextStyle(fontWeight: isRead ? FontWeight.normal : FontWeight.bold),
                          ),
                          subtitle: Text(item['message'] ?? ''),
                          onTap: isRead ? null : () => _markRead(item['id']),
                        );
                      },
                    ),
            ),
    );
  }
}
