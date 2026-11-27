import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../l10n/app_localizations.dart';

class TopQuestionsScreen extends StatefulWidget {
  const TopQuestionsScreen({super.key});

  @override
  State<TopQuestionsScreen> createState() => _TopQuestionsScreenState();
}

class _TopQuestionsScreenState extends State<TopQuestionsScreen> {
  List<Map<String, dynamic>> _faqs = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _loadFaqs();
  }

  Future<void> _loadFaqs() async {
    try {
      final raw = await rootBundle.loadString('assets/faq/faq_en.json');
      final list = jsonDecode(raw) as List<dynamic>;
      if (mounted) {
        setState(() {
          _faqs = list.cast<Map<String, dynamic>>();
          _loading = false;
        });
      }
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;

    return Scaffold(
      appBar: AppBar(title: Text(l10n.topQuestionsTitle)),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : ListView.builder(
              padding: const EdgeInsets.all(12),
              itemCount: _faqs.length,
              itemBuilder: (ctx, i) {
                final item = _faqs[i];
                return Card(
                  margin: const EdgeInsets.only(bottom: 8),
                  child: ExpansionTile(
                    title: Text(
                      item['q']?.toString() ?? '',
                      style: const TextStyle(fontWeight: FontWeight.w600),
                    ),
                    children: [
                      Padding(
                        padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
                        child: Text(item['a']?.toString() ?? ''),
                      ),
                    ],
                  ),
                );
              },
            ),
    );
  }
}
