import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:package_info_plus/package_info_plus.dart';

import '../core/network/auth_http_client.dart';
import '../l10n/app_localizations.dart';
import '../screens/about_us_screen.dart';
import '../screens/app_info_screen.dart';
import '../screens/e_contact_screen.dart';
import '../screens/edit_profile_screen.dart';
import '../screens/login_screen.dart';
import '../screens/settings_screen.dart';
import '../screens/sos_history_screen.dart';
import '../screens/top_questions_screen.dart';
import '../services/auth_storage_service.dart';
import '../services/sos_queue_service.dart';
import '../widgets/app_colors.dart';

enum DrawerRouteItem {
  home,
  profile,
  eContact,
  sosHistory,
  settings,
  appInfo,
  topQuestions,
}

class EmergencyDrawer extends StatefulWidget {
  final DrawerRouteItem currentRoute;
  final VoidCallback? onProfileUpdated;

  const EmergencyDrawer({
    super.key,
    this.currentRoute = DrawerRouteItem.home,
    this.onProfileUpdated,
  });

  @override
  State<EmergencyDrawer> createState() => _EmergencyDrawerState();
}

class _EmergencyDrawerState extends State<EmergencyDrawer> {
  String _fullName = 'EmergencyIQ User';
  String _phone = 'Tap Profile to complete';
  String _version = '1.0.0';

  @override
  void initState() {
    super.initState();
    _loadHeaderAndVersion();
  }

  Future<void> _loadHeaderAndVersion() async {
    final profile = await AuthStorageService.getUserProfile();
    String ver = '1.0.0';
    try {
      final info = await PackageInfo.fromPlatform();
      ver = info.version;
    } catch (_) {}

    if (mounted) {
      setState(() {
        final name = profile?['full_name']?.toString().trim();
        final phone = profile?['phone']?.toString().trim();
        if (name != null && name.isNotEmpty) _fullName = name;
        if (phone != null && phone.isNotEmpty) _phone = phone;
        _version = ver;
      });
    }
  }

  Future<void> _handleLogout() async {
    final l10n = AppLocalizations.of(context)!;
    final choice = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(l10n.logoutConfirmTitle),
        content: Text(l10n.logoutConfirmMessage),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop('cancel'),
            child: Text(l10n.cancelBtn),
          ),
          TextButton(
            onPressed: () => Navigator.of(ctx).pop('keep'),
            child: Text(l10n.logoutKeepQueue),
          ),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: Colors.red),
            onPressed: () => Navigator.of(ctx).pop('clear'),
            child: Text(l10n.logoutClearQueue),
          ),
        ],
      ),
    );

    if (choice == null || choice == 'cancel') return;
    try {
      final rt = await AuthStorageService.getRefreshToken();
      await AuthHttpClient.post(
        '/api/v1/auth/logout',
        body: jsonEncode({'refresh_token': rt}),
      );
    } catch (_) {}
    if (choice == 'clear') {
      await SosQueueService().clearQueue();
    }
    await AuthStorageService.clearAuth();
    if (!mounted) return;
    Navigator.of(context).pop(); // Close drawer
    Navigator.of(context).pushReplacement(
      MaterialPageRoute(builder: (_) => const LoginScreen()),
    );
  }

  Widget _buildItem({
    required IconData icon,
    required String label,
    required DrawerRouteItem route,
    required VoidCallback onTap,
  }) {
    final selected = widget.currentRoute == route;
    return ListTile(
      leading: Icon(
        icon,
        color: selected ? AppColors.primary : null,
      ),
      title: Text(
        label,
        style: TextStyle(
          fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
          color: selected ? AppColors.primary : null,
        ),
      ),
      selected: selected,
      selectedTileColor: AppColors.primary.withValues(alpha: 0.1),
      minVerticalPadding: 14,
      onTap: () {
        Navigator.of(context).pop();
        if (!selected) {
          onTap();
        }
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final initial = _fullName.isNotEmpty ? _fullName[0].toUpperCase() : 'E';

    return Drawer(
      child: SafeArea(
        child: Column(
          children: [
            UserAccountsDrawerHeader(
              decoration: const BoxDecoration(
                color: AppColors.primary,
              ),
              currentAccountPicture: CircleAvatar(
                backgroundColor: Colors.white,
                child: Text(
                  initial,
                  style: const TextStyle(
                    fontSize: 26,
                    fontWeight: FontWeight.bold,
                    color: AppColors.primary,
                  ),
                ),
              ),
              accountName: Text(
                _fullName,
                style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16),
              ),
              accountEmail: Text(_phone),
            ),
            Expanded(
              child: ListView(
                padding: EdgeInsets.zero,
                children: [
                  _buildItem(
                    icon: Icons.home_outlined,
                    label: l10n.drawerHome,
                    route: DrawerRouteItem.home,
                    onTap: () => Navigator.of(context).popUntil((r) => r.isFirst),
                  ),
                  _buildItem(
                    icon: Icons.person_outline,
                    label: l10n.drawerProfile,
                    route: DrawerRouteItem.profile,
                    onTap: () async {
                      await Navigator.of(context).push(
                        MaterialPageRoute(builder: (_) => const EditProfileScreen()),
                      );
                      widget.onProfileUpdated?.call();
                    },
                  ),
                  _buildItem(
                    icon: Icons.contacts_outlined,
                    label: l10n.drawerEContact,
                    route: DrawerRouteItem.eContact,
                    onTap: () => Navigator.of(context).push(
                      MaterialPageRoute(builder: (_) => const EContactScreen()),
                    ),
                  ),
                  _buildItem(
                    icon: Icons.history_outlined,
                    label: l10n.drawerSosHistory,
                    route: DrawerRouteItem.sosHistory,
                    onTap: () => Navigator.of(context).push(
                      MaterialPageRoute(builder: (_) => const SosHistoryScreen()),
                    ),
                  ),
                  _buildItem(
                    icon: Icons.settings_outlined,
                    label: l10n.drawerSettings,
                    route: DrawerRouteItem.settings,
                    onTap: () => Navigator.of(context).push(
                      MaterialPageRoute(builder: (_) => const SettingsScreen()),
                    ),
                  ),
                  _buildItem(
                    icon: Icons.info_outline,
                    label: l10n.drawerAppInfo,
                    route: DrawerRouteItem.appInfo,
                    onTap: () => Navigator.of(context).push(
                      MaterialPageRoute(builder: (_) => const AppInfoScreen()),
                    ),
                  ),
                  _buildItem(
                    icon: Icons.help_outline,
                    label: l10n.drawerTopQuestions,
                    route: DrawerRouteItem.topQuestions,
                    onTap: () => Navigator.of(context).push(
                      MaterialPageRoute(builder: (_) => const TopQuestionsScreen()),
                    ),
                  ),
                  const Divider(),
                  ListTile(
                    leading: const Icon(Icons.logout, color: Colors.red),
                    title: Text(
                      l10n.drawerLogout,
                      style: const TextStyle(color: Colors.red, fontWeight: FontWeight.w600),
                    ),
                    onTap: _handleLogout,
                  ),
                ],
              ),
            ),
            const Divider(height: 1),
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 16),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    l10n.versionLabel(_version),
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                  InkWell(
                    onTap: () {
                      Navigator.of(context).pop();
                      Navigator.of(context).push(
                        MaterialPageRoute(builder: (_) => const AboutUsScreen()),
                      );
                    },
                    child: Text(
                      l10n.aboutUsTitle,
                      style: TextStyle(
                        fontSize: 12,
                        color: AppColors.primary,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
