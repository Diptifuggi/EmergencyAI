import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

import '../core/network/api_client.dart';
import '../services/auth_storage_service.dart';

class RegisterScreen extends StatefulWidget {
  const RegisterScreen({super.key});

  @override
  State<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen> {
  final _formKey = GlobalKey<FormState>();

  // Mandatory fields
  final _nameController = TextEditingController();
  final _phoneController = TextEditingController();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();

  // Optional profile details
  final _altPhoneController = TextEditingController();
  final _guardianPhoneController = TextEditingController();
  final _guardianRelationController = TextEditingController();
  final _addressController = TextEditingController();
  final _ageController = TextEditingController();
  final _allergiesController = TextEditingController();
  final _historyController = TextEditingController();

  String _bloodGroup = 'unknown';
  bool _medicalConsent = false;
  bool _showProfileDetails = false;
  bool _isLoading = false;
  String? _errorMessage;

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
  void dispose() {
    _nameController.dispose();
    _phoneController.dispose();
    _emailController.dispose();
    _passwordController.dispose();
    _altPhoneController.dispose();
    _guardianPhoneController.dispose();
    _guardianRelationController.dispose();
    _addressController.dispose();
    _ageController.dispose();
    _allergiesController.dispose();
    _historyController.dispose();
    super.dispose();
  }

  Future<void> _handleRegister() async {
    if (!_formKey.currentState!.validate()) return;

    if ((_allergiesController.text.trim().isNotEmpty ||
            _historyController.text.trim().isNotEmpty) &&
        !_medicalConsent) {
      setState(() {
        _errorMessage = 'Consent is required to save allergies or medical history.';
      });
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final baseUrl = await ApiClient.getBaseUrl();
      final uri = Uri.parse('$baseUrl/api/v1/auth/register');

      final body = {
        'username': _nameController.text.trim().replaceAll(' ', '_').toLowerCase(),
        'email': _emailController.text.trim(),
        'password': _passwordController.text,
        'full_name': _nameController.text.trim(),
        'phone': _phoneController.text.trim(),
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

      final response = await http
          .post(uri, headers: {'Content-Type': 'application/json'}, body: jsonEncode(body))
          .timeout(const Duration(seconds: 15));

      if (response.statusCode == 201) {
        // Auto-login to obtain JWT tokens
        await _autoLogin(_emailController.text.trim(), _passwordController.text);
      } else {
        final err = jsonDecode(response.body);
        setState(() {
          _errorMessage = err['detail'] ?? 'Registration failed. Please check inputs.';
        });
      }
    } catch (e) {
      setState(() {
        _errorMessage = 'Connection error: unable to register.';
      });
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _autoLogin(String email, String password) async {
    try {
      final baseUrl = await ApiClient.getBaseUrl();
      final uri = Uri.parse('$baseUrl/api/v1/auth/login');
      final res = await http.post(
        uri,
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'email': email, 'password': password}),
      );
      if (res.statusCode == 200) {
        final data = jsonDecode(res.body);
        await AuthStorageService.saveTokens(
          accessToken: data['access_token'],
          refreshToken: data['refresh_token'],
        );
        if (mounted) {
          Navigator.of(context).pop(true);
        }
      }
    } catch (_) {
      if (mounted) Navigator.of(context).pop(true);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Create Account'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              if (_errorMessage != null)
                Container(
                  padding: const EdgeInsets.all(12),
                  margin: const EdgeInsets.only(bottom: 16),
                  decoration: BoxDecoration(
                    color: Colors.red.shade50,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: Colors.red.shade200),
                  ),
                  child: Text(
                    _errorMessage!,
                    style: TextStyle(color: Colors.red.shade800, fontSize: 13),
                  ),
                ),

              // Mandatory section
              const Text('Personal Information', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
              const SizedBox(height: 12),
              TextFormField(
                controller: _nameController,
                decoration: const InputDecoration(labelText: 'Full Name *', prefixIcon: Icon(Icons.person)),
                validator: (v) => v == null || v.trim().isEmpty ? 'Full name is required' : null,
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _phoneController,
                decoration: const InputDecoration(labelText: 'Phone Number (Indian E.164) *', prefixIcon: Icon(Icons.phone)),
                keyboardType: TextInputType.phone,
                validator: (v) {
                  if (v == null || v.trim().isEmpty) return 'Phone number is required';
                  final clean = v.trim().replaceAll(' ', '').replaceAll('-', '');
                  if (!RegExp(r'^(\+91|91|0)?[6-9]\d{9}$').hasMatch(clean)) {
                    return 'Enter a valid 10-digit Indian phone number';
                  }
                  return null;
                },
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _emailController,
                decoration: const InputDecoration(labelText: 'Email Address *', prefixIcon: Icon(Icons.email)),
                keyboardType: TextInputType.emailAddress,
                validator: (v) => v == null || !v.contains('@') ? 'Valid email is required' : null,
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _passwordController,
                decoration: const InputDecoration(labelText: 'Password (min 8 chars) *', prefixIcon: Icon(Icons.lock)),
                obscureText: true,
                validator: (v) => v == null || v.length < 8 ? 'Password must be at least 8 characters' : null,
              ),

              const SizedBox(height: 24),
              // Optional details toggle
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text('Emergency Profile Details', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                  TextButton.icon(
                    icon: Icon(_showProfileDetails ? Icons.expand_less : Icons.expand_more),
                    label: Text(_showProfileDetails ? 'Hide' : 'Add Optional Details'),
                    onPressed: () => setState(() => _showProfileDetails = !_showProfileDetails),
                  ),
                ],
              ),

              if (_showProfileDetails) ...[
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
                        decoration: const InputDecoration(labelText: 'Parent/Guardian Phone', prefixIcon: Icon(Icons.emergency)),
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
                  decoration: const InputDecoration(labelText: 'Home Address', prefixIcon: Icon(Icons.home)),
                  maxLines: 2,
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: TextFormField(
                        controller: _ageController,
                        decoration: const InputDecoration(labelText: 'Age (1-120)', prefixIcon: Icon(Icons.cake)),
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
                  decoration: const InputDecoration(labelText: 'Allergies (e.g. penicillin, nuts)', prefixIcon: Icon(Icons.warning_amber)),
                  maxLines: 2,
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: _historyController,
                  decoration: const InputDecoration(labelText: 'Medical History (e.g. asthma, diabetes)', prefixIcon: Icon(Icons.medical_information)),
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
                      'I consent to sharing my medical details with emergency responders and operators when an SOS is triggered.',
                      style: TextStyle(fontSize: 13, fontWeight: FontWeight.w500),
                    ),
                    value: _medicalConsent,
                    onChanged: (v) => setState(() => _medicalConsent = v ?? false),
                    controlAffinity: ListTileControlAffinity.leading,
                  ),
                ),
              ],

              const SizedBox(height: 28),
              ElevatedButton(
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  backgroundColor: Colors.red.shade700,
                  foregroundColor: Colors.white,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                ),
                onPressed: _isLoading ? null : _handleRegister,
                child: _isLoading
                    ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                    : const Text('Create Account', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
