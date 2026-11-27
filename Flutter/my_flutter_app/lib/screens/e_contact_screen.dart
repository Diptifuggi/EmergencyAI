import 'package:flutter/material.dart';

import '../l10n/app_localizations.dart';
import '../services/auth_storage_service.dart';
import '../services/home_feature_api_service.dart';
import '../widgets/app_colors.dart';

class EContactScreen extends StatefulWidget {
  const EContactScreen({super.key});

  @override
  State<EContactScreen> createState() => _EContactScreenState();
}

class _EContactScreenState extends State<EContactScreen> {
  List<Map<String, dynamic>> _contacts = [];
  bool _loading = true;
  String? _error;

  String? _profileGuardianPhone;
  String? _profileGuardianRelation;
  String? _profileAltPhone;

  static final RegExp _indianPhoneRegex = RegExp(r'^(\+91|91|0)?([6-9]\d{9})$');

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final profile = await AuthStorageService.getUserProfile();
      final list = await HomeFeatureApiService.listEmergencyContacts();
      if (!mounted) return;
      setState(() {
        _contacts = list;
        _profileGuardianPhone = profile?['guardian_phone']?.toString();
        _profileGuardianRelation = profile?['guardian_relation']?.toString() ?? 'Guardian';
        _profileAltPhone = profile?['alternate_phone']?.toString();
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

  String? _normalizePhone(String input) {
    final cleaned = input.trim().replaceAll(' ', '').replaceAll('-', '');
    final m = _indianPhoneRegex.firstMatch(cleaned);
    if (m == null) return null;
    return '+91${m.group(2)}';
  }

  bool _hasPhone(String? phone) {
    if (phone == null || phone.trim().isEmpty) return false;
    final norm = _normalizePhone(phone) ?? phone;
    return _contacts.any((c) => c['phone'] == norm);
  }

  Future<void> _openFormDialog({Map<String, dynamic>? existing}) async {
    final l10n = AppLocalizations.of(context)!;
    if (existing == null && _contacts.length >= 5) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(l10n.eContactLimitReached)),
      );
      return;
    }

    final nameCtrl = TextEditingController(text: existing?['name'] ?? '');
    final phoneCtrl = TextEditingController(text: existing?['phone'] ?? '+91');
    final relCtrl = TextEditingController(text: existing?['relation'] ?? 'Family');
    bool notifyOnSos = existing?['notify_on_sos'] ?? true;
    bool isPrimary = existing?['is_primary'] ?? false;
    final formKey = GlobalKey<FormState>();

    final saved = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialogState) => AlertDialog(
          title: Text(existing == null ? l10n.eContactAddBtn : 'Edit Contact'),
          content: Form(
            key: formKey,
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  TextFormField(
                    controller: nameCtrl,
                    decoration: const InputDecoration(labelText: 'Name'),
                    validator: (v) => (v == null || v.trim().isEmpty) ? 'Required' : null,
                  ),
                  const SizedBox(height: 8),
                  TextFormField(
                    controller: phoneCtrl,
                    keyboardType: TextInputType.phone,
                    decoration: const InputDecoration(
                      labelText: 'Phone (+91 default)',
                      hintText: '+919876543210',
                    ),
                    validator: (v) {
                      if (v == null || _normalizePhone(v) == null) {
                        return 'Enter valid 10-digit Indian phone number';
                      }
                      return null;
                    },
                  ),
                  const SizedBox(height: 8),
                  TextFormField(
                    controller: relCtrl,
                    decoration: const InputDecoration(labelText: 'Relation'),
                    validator: (v) => (v == null || v.trim().isEmpty) ? 'Required' : null,
                  ),
                  SwitchListTile(
                    contentPadding: EdgeInsets.zero,
                    title: const Text('Notify on SOS'),
                    value: notifyOnSos,
                    onChanged: (v) => setDialogState(() => notifyOnSos = v),
                  ),
                  SwitchListTile(
                    contentPadding: EdgeInsets.zero,
                    title: const Text('Primary Contact'),
                    value: isPrimary,
                    onChanged: (v) => setDialogState(() => isPrimary = v),
                  ),
                ],
              ),
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(false),
              child: Text(l10n.cancelBtn),
            ),
            FilledButton(
              onPressed: () async {
                if (!formKey.currentState!.validate()) return;
                final payload = {
                  'name': nameCtrl.text.trim(),
                  'phone': _normalizePhone(phoneCtrl.text)!,
                  'relation': relCtrl.text.trim(),
                  'notify_on_sos': notifyOnSos,
                  'is_primary': isPrimary,
                };
                try {
                  if (existing == null) {
                    await HomeFeatureApiService.createEmergencyContact(payload);
                  } else {
                    await HomeFeatureApiService.updateEmergencyContact(existing['id'], payload);
                  }
                  if (ctx.mounted) Navigator.of(ctx).pop(true);
                } catch (e) {
                  if (ctx.mounted) {
                    ScaffoldMessenger.of(ctx).showSnackBar(SnackBar(content: Text(e.toString())));
                  }
                }
              },
              child: const Text('Save'),
            ),
          ],
        ),
      ),
    );

    if (saved == true) {
      await _loadData();
    }
  }

  Future<void> _quickAddSuggestion(String name, String phone, String relation) async {
    final norm = _normalizePhone(phone);
    if (norm == null) return;
    try {
      await HomeFeatureApiService.createEmergencyContact({
        'name': name,
        'phone': norm,
        'relation': relation,
        'notify_on_sos': true,
        'is_primary': _contacts.isEmpty,
      });
      await _loadData();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
      }
    }
  }

  Future<void> _deleteContact(String id) async {
    try {
      await HomeFeatureApiService.deleteEmergencyContact(id);
      await _loadData();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final showGuardianSuggest = _profileGuardianPhone != null &&
        _profileGuardianPhone!.isNotEmpty &&
        !_hasPhone(_profileGuardianPhone) &&
        _contacts.length < 5;
    final showAltSuggest = _profileAltPhone != null &&
        _profileAltPhone!.isNotEmpty &&
        !_hasPhone(_profileAltPhone) &&
        _contacts.length < 5;

    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.eContactTitle),
      ),
      floatingActionButton: _contacts.length < 5
          ? FloatingActionButton.extended(
              onPressed: () => _openFormDialog(),
              backgroundColor: AppColors.primary,
              foregroundColor: Colors.white,
              icon: const Icon(Icons.person_add),
              label: Text(l10n.eContactAddBtn),
            )
          : null,
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(_error!),
                      const SizedBox(height: 12),
                      ElevatedButton(onPressed: _loadData, child: const Text('Retry')),
                    ],
                  ),
                )
              : RefreshIndicator(
                  onRefresh: _loadData,
                  child: ListView(
                    padding: const EdgeInsets.all(16),
                    children: [
                      if (showGuardianSuggest || showAltSuggest) ...[
                        Card(
                          color: Colors.blue.withValues(alpha: 0.08),
                          child: Padding(
                            padding: const EdgeInsets.all(12),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  l10n.eContactSuggestionTitle,
                                  style: const TextStyle(fontWeight: FontWeight.bold),
                                ),
                                if (showGuardianSuggest)
                                  ListTile(
                                    contentPadding: EdgeInsets.zero,
                                    title: Text('$_profileGuardianRelation ($_profileGuardianPhone)'),
                                    trailing: TextButton(
                                      onPressed: () => _quickAddSuggestion(
                                        _profileGuardianRelation ?? 'Guardian',
                                        _profileGuardianPhone!,
                                        _profileGuardianRelation ?? 'Guardian',
                                      ),
                                      child: Text(l10n.eContactAddSuggested),
                                    ),
                                  ),
                                if (showAltSuggest)
                                  ListTile(
                                    contentPadding: EdgeInsets.zero,
                                    title: Text('Alternate ($_profileAltPhone)'),
                                    trailing: TextButton(
                                      onPressed: () => _quickAddSuggestion(
                                        'Alternate Contact',
                                        _profileAltPhone!,
                                        'Family',
                                      ),
                                      child: Text(l10n.eContactAddSuggested),
                                    ),
                                  ),
                              ],
                            ),
                          ),
                        ),
                        const SizedBox(height: 12),
                      ],
                      if (_contacts.isEmpty)
                        Padding(
                          padding: const EdgeInsets.symmetric(vertical: 48),
                          child: Center(child: Text(l10n.eContactEmpty)),
                        )
                      else
                        ..._contacts.map((c) {
                          final isPrimary = c['is_primary'] == true;
                          return Card(
                            margin: const EdgeInsets.only(bottom: 10),
                            child: ListTile(
                              leading: CircleAvatar(
                                backgroundColor: isPrimary ? AppColors.primary : Colors.grey.shade300,
                                child: Icon(
                                  Icons.person,
                                  color: isPrimary ? Colors.white : Colors.black87,
                                ),
                              ),
                              title: Row(
                                children: [
                                  Expanded(
                                    child: Text(
                                      c['name'] ?? '',
                                      style: const TextStyle(fontWeight: FontWeight.w600),
                                    ),
                                  ),
                                  if (isPrimary)
                                    Container(
                                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                                      decoration: BoxDecoration(
                                        color: AppColors.primary.withValues(alpha: 0.15),
                                        borderRadius: BorderRadius.circular(12),
                                      ),
                                      child: const Text(
                                        'PRIMARY',
                                        style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: AppColors.primary),
                                      ),
                                    ),
                                ],
                              ),
                              subtitle: Text('${c['phone']} • ${c['relation']}'),
                              trailing: PopupMenuButton<String>(
                                onSelected: (val) {
                                  if (val == 'edit') _openFormDialog(existing: c);
                                  if (val == 'delete') _deleteContact(c['id']);
                                },
                                itemBuilder: (_) => const [
                                  PopupMenuItem(value: 'edit', child: Text('Edit')),
                                  PopupMenuItem(value: 'delete', child: Text('Delete')),
                                ],
                              ),
                            ),
                          );
                        }),
                    ],
                  ),
                ),
    );
  }
}
