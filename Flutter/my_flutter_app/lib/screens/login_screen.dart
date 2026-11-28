import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

import '../core/network/api_client.dart';
import '../services/auth_storage_service.dart';
import 'register_screen.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _isLoading = false;
  String? _errorMessage;

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _handleLogin() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final baseUrl = await ApiClient.getBaseUrl();
      final uri = Uri.parse('$baseUrl/api/v1/auth/login');

      final res = await http.post(
        uri,
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'email': _emailController.text.trim(),
          'password': _passwordController.text,
        }),
      ).timeout(const Duration(seconds: 15));

      if (res.statusCode == 200) {
        final data = jsonDecode(res.body);
        final accessToken = data['access_token'] as String;
        final refreshToken = data['refresh_token'] as String;

        // Verify user role: block Operator/Supervisor/Admin from citizen mobile app
        final meRes = await http.get(
          Uri.parse('$baseUrl/api/v1/auth/me'),
          headers: {
            'Accept': 'application/json',
            'Authorization': 'Bearer $accessToken',
          },
        ).timeout(const Duration(seconds: 10));

        if (meRes.statusCode == 200) {
          final me = jsonDecode(meRes.body) as Map<String, dynamic>;
          final role = (me['role_name'] ?? '').toString().toLowerCase();
          if (role != 'user') {
            setState(() {
              _errorMessage =
                  'This app is for citizens only. Please sign in on the Operator Dashboard.';
            });
            return;
          }
        }

        await AuthStorageService.saveTokens(
          accessToken: accessToken,
          refreshToken: refreshToken,
        );

        // Cache citizen profile for Drawer & E-Contact suggestions
        try {
          final profRes = await http.get(
            Uri.parse('$baseUrl/api/v1/users/me/profile'),
            headers: {
              'Accept': 'application/json',
              'Authorization': 'Bearer $accessToken',
            },
          ).timeout(const Duration(seconds: 10));
          if (profRes.statusCode == 200) {
            await AuthStorageService.saveUserProfile(
              jsonDecode(profRes.body) as Map<String, dynamic>,
            );
          }
        } catch (_) {}

        if (mounted) Navigator.of(context).pop(true);
      } else if (res.statusCode == 429) {
        setState(() => _errorMessage = 'Too many failed login attempts. Please try again later.');
      } else {
        setState(() => _errorMessage = 'Invalid email or password.');
      }
    } catch (e) {
      setState(() => _errorMessage = 'Connection error: failed to connect to backend.');
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Sign In')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const SizedBox(height: 20),
            const Icon(Icons.shield_outlined, size: 64, color: Colors.redAccent),
            const SizedBox(height: 16),
            const Center(
              child: Text(
                'EmergencyIQ Citizen Access',
                style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
              ),
            ),
            const SizedBox(height: 24),
            if (_errorMessage != null)
              Container(
                padding: const EdgeInsets.all(12),
                margin: const EdgeInsets.only(bottom: 16),
                decoration: BoxDecoration(
                  color: Colors.red.shade50,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.red.shade200),
                ),
                child: Text(_errorMessage!, style: TextStyle(color: Colors.red.shade800, fontSize: 13)),
              ),
            TextFormField(
              controller: _emailController,
              decoration: const InputDecoration(labelText: 'Email Address', prefixIcon: Icon(Icons.email)),
              keyboardType: TextInputType.emailAddress,
            ),
            const SizedBox(height: 16),
            TextFormField(
              controller: _passwordController,
              decoration: const InputDecoration(labelText: 'Password', prefixIcon: Icon(Icons.lock)),
              obscureText: true,
            ),
            const SizedBox(height: 24),
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 16),
                backgroundColor: Colors.red.shade700,
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
              ),
              onPressed: _isLoading ? null : _handleLogin,
              child: _isLoading
                  ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                  : const Text('Sign In', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
            ),
            const SizedBox(height: 16),
            TextButton(
              onPressed: () {
                Navigator.of(context).push(MaterialPageRoute(builder: (_) => const RegisterScreen()));
              },
              child: const Text('Don\'t have an account? Register with Emergency Profile'),
            ),
          ],
        ),
      ),
    );
  }
}
