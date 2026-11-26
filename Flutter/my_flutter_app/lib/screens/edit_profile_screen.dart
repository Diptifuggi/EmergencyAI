import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

import '../core/network/api_client.dart';
import '../services/auth_storage_service.dart';

class EditProfileScreen extends StatefulWidget {
  const EditProfileScreen({super.key});

  @override
  State<EditProfileScreen> createState() => _EditProfileScreenState();
}

class _EditProfileScreenState extends State<EditProfileScreen> {
  final _formKey = GlobalKey<FormState>();

  final _nameController = TextEditingController();
  final _phoneController = TextEditingController();
  final _altPhoneController = TextEditingController();
  final _guardianPhoneController = TextEditingController();
  final _guardianRelationController = TextEditingController();
  final _addressController = TextEditingController();
  final _ageController = TextEditingController();
  final _allergiesController = TextEditingController();
  final _historyController = TextEditingController();

  String _bloodGroup = 'unknown';
  bool _medicalConsent = false;
  bool _isLoading = true;
  bool _isSaving = false;
  String? _statusMessage;
  bool _isError = false;

  static const List<String> _bloodGroups = [
    'unknown',
    'A+',
    'A-',
    'B+',
    'B-',
    'AB+',
    'AB-',
    'O+',
    'O-'
  ];

  @override
  void initState() {
    super.initState();
    _fetchProfile();
  }

  @override
  void dispose() {
    _nameController.dispose();
    _phoneController.dispose();
    _altPhoneController.dispose();
    _guardianPhoneController.dispose();
    _guardianRelationController.dispose();
    _addressController.dispose();
    _ageController.dispose();
    _allergiesController.dispose();
    _historyController.dispose();
    super.dispose();
  }

  Future<void> _fetchProfile() async {
    setState(() => _isLoading = true);
    try {
      final baseUrl = await ApiClient.getBaseUrl();
      final uri = Uri.parse('$baseUrl/api/v1/users/me/profile');
      final token = await AuthStorageService.getAccessToken();

      final res = await http.get(uri, headers: {
        'Accept': 'application/json',
        if (token != null) 'Authorization': 'Bearer $token',
      }).timeout(const Duration(seconds: 10));

      if (res.statusCode == 200) {
        final data = jsonDecode(res.body);
        _nameController.text = data['full_name'] ?? '';
        _phoneController.text = data['phone'] ?? '';
        _altPhoneController.text = data['alternate_phone'] ?? '';
        _guardianPhoneController.text = data['guardian_phone'] ?? '';
        _guardianRelationController.text = data['guardian_relation'] ?? '';
        _addressController.text = data['address'] ?? '';
        _ageController.text = data['age'] != null ? data['age'].toString() : '';
        _bloodGroup = data['blood_group'] ?? 'unknown';
        _allergiesController.text = data['allergies'] ?? '';
        _historyController.text = data['medical_history'] ?? '';
        _medicalConsent = data['medical_consent'] ?? false;
      }
    } catch (e) {
      debugPrint('[EditProfile] Failed to load: $e');
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _saveProfile() async {
    if (!_formKey.currentState!.validate()) return;

    if ((_allergiesController.text.trim().isNotEmpty ||
            _historyController.text.trim().isNotEmpty) &&
        !_medicalConsent) {
      setState(() {
        _statusMessage = 'Consent is required to save medical info.';
        _isError = true;
      });
      return;
    }

    setState(() {
      _isSaving = true;
      _statusMessage = null;
    });

    try {
      final baseUrl = await ApiClient.getBaseUrl();
      final uri = Uri.parse('$baseUrl/api/v1/users/me/profile');
      final token = await AuthStorageService.getAccessToken();

      final body = {
        'full_name': _nameController.text.trim().isEmpty ? null : _nameController.text.trim(),
        'phone': _phoneController.text.trim().isEmpty ? null : _phoneController.text.trim(),
        'alternate_phone': _altPhoneController.text.trim().isEmpty ? null : _altPhoneController.text.trim(),
        'guardian_phone': _guardianPhoneController.text.trim().isEmpty ? null : _guardianPhoneController.text.trim(),
        'guardian_relation': _guardianRelationController.text.trim().isEmpty ? null : _guardianRelationController.text.trim(),
        'address': _addressController.text.trim().isEmpty ? null : _addressController.text.trim(),
        'age': int.tryParse(_ageController.text.trim()),
        'blood_group': _bloodGroup,
        'allergies': _allergiesController.text.trim().isEmpty ? null : _allergiesController.text.trim(),
        'medical_history': _historyController.text.trim().isEmpty ? null : _historyController.text.trim(),
        'medical_consent': _medicalConsent,
      };

      final res = await http.put(
        uri,
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          if (token != null) 'Authorization': 'Bearer $token',
        },
        body: jsonEncode(body),
      ).timeout(const Duration(seconds: 15));

      if (res.statusCode == 200) {
        setState(() {
          _statusMessage = 'Profile updated successfully!';
          _isError = false;
        });
        await AuthStorageService.saveUserProfile(jsonDecode(res.body));
      } else {
        final err = jsonDecode(res.body);
        setState(() {
          _statusMessage = err['detail'] ?? 'Failed to update profile.';
          _isError = true;
        });
      }
    } catch (e) {
      setState(() {
        _statusMessage = 'Connection error: failed to save profile.';
        _isError = true;
      });
    } finally {
      if (mounted) setState(() => _isSaving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Edit Emergency Profile'),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : SingleChildScrollView(
              padding: const EdgeInsets.all(20),
              child: Form(
                key: _formKey,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    if (_statusMessage != null)
                      Container(
                        padding: const EdgeInsets.all(12),
                        margin: const EdgeInsets.only(bottom: 16),
                        decoration: BoxDecoration(
                          color: _isError ? Colors.red.shade50 : Colors.green.shade50,
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: _isError ? Colors.red.shade200 : Colors.green.shade200),
                        ),
                        child: Text(
                          _statusMessage!,
                          style: TextStyle(color: _isError ? Colors.red.shade800 : Colors.green.shade800, fontSize: 13),
                        ),
                      ),
                    TextFormField(
                      controller: _nameController,
                      decoration: const InputDecoration(labelText: 'Full Name', prefixIcon: Icon(Icons.person)),
                    ),
                    const SizedBox(height: 12),
                    TextFormField(
                      controller: _phoneController,
                      decoration: const InputDecoration(labelText: 'Phone Number', prefixIcon: Icon(Icons.phone)),
                      keyboardType: TextInputType.phone,
                    ),
                    const SizedBox(height: 12),
                    TextFormField(
                      controller: _altPhoneController,
                      decoration: const InputDecoration(labelText: 'Alternate Phone', prefixIcon: Icon(Icons.phone_android)),
                      keyboardType: TextInputType.phone,
                    ),
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        Expanded(
                          flex: 2,
                          child: TextFormField(
                            controller: _guardianPhoneController,
                            decoration: const InputDecoration(labelText: 'Guardian Phone', prefixIcon: Icon(Icons.emergency)),
                            keyboardType: TextInputType.phone,
                          ),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          flex: 1,
                          child: TextFormField(
                            controller: _guardianRelationController,
                            decoration: const InputDecoration(labelText: 'Relation'),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    TextFormField(
                      controller: _addressController,
                      decoration: const InputDecoration(labelText: 'Address', prefixIcon: Icon(Icons.home)),
                      maxLines: 2,
                    ),
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        Expanded(
                          child: TextFormField(
                            controller: _ageController,
                            decoration: const InputDecoration(labelText: 'Age', prefixIcon: Icon(Icons.cake)),
                            keyboardType: TextInputType.number,
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: DropdownButtonFormField<String>(
                            value: _bloodGroup,
                            decoration: const InputDecoration(labelText: 'Blood Group'),
                            items: _bloodGroups.map((bg) => DropdownMenuItem(value: bg, child: Text(bg))).toList(),
                            onChanged: (v) => setState(() => _bloodGroup = v ?? 'unknown'),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    TextFormField(
                      controller: _allergiesController,
                      decoration: const InputDecoration(labelText: 'Allergies', prefixIcon: Icon(Icons.warning_amber)),
                      maxLines: 2,
                    ),
                    const SizedBox(height: 12),
                    TextFormField(
                      controller: _historyController,
                      decoration: const InputDecoration(labelText: 'Medical History', prefixIcon: Icon(Icons.medical_information)),
                      maxLines: 2,
                    ),
                    const SizedBox(height: 16),
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: Colors.blue.shade50,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: Colors.blue.shade200),
                      ),
                      child: CheckboxListTile(
                        contentPadding: EdgeInsets.zero,
                        title: const Text(
                          'I consent to sharing my medical details with emergency operators during an SOS.',
                          style: TextStyle(fontSize: 13, fontWeight: FontWeight.w500),
                        ),
                        value: _medicalConsent,
                        onChanged: (v) => setState(() => _medicalConsent = v ?? false),
                        controlAffinity: ListTileControlAffinity.leading,
                      ),
                    ),
                    const SizedBox(height: 24),
                    ElevatedButton(
                      style: ElevatedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(vertical: 16),
                        backgroundColor: Colors.blue.shade700,
                        foregroundColor: Colors.white,
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                      ),
                      onPressed: _isSaving ? null : _saveProfile,
                      child: _isSaving
                          ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                          : const Text('Save Profile Changes', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                    ),
                  ],
                ),
              ),
            ),
    );
  }
}
