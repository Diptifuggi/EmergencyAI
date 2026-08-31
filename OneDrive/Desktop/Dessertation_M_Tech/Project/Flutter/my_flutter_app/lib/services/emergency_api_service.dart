import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart' show debugPrint;
import 'package:http/http.dart' as http;

import '../core/language/language_mapper.dart';
import '../core/network/api_client.dart';
import '../models/emergency_call.dart';

class EmergencyApiService {
  String _validatedLanguage(String language) {
    final canonical = LanguageMapper.toApiCode(language);
    if (!LanguageMapper.isValidApiCode(canonical)) {
      throw ApiException(
        'Invalid EmergencyIQ language "$language". Expected en, hi, gu, or mr.',
      );
    }
    return canonical!;
  }

  Future<EmergencyCall> submitTextEmergency({
    required String text,
    required String language,
    double? latitude,
    double? longitude,
    double? locationAccuracy,
    DateTime? locationTimestamp,
    Map<String, dynamic>? clientMetadata,
  }) async {
    final baseUrl = await ApiClient.getBaseUrl();
    debugPrint('[EmergencyIQ] POST $baseUrl/api/v1/emergency-calls/text');
    final response = await ApiClient.client.post(
      Uri.parse('$baseUrl/api/v1/emergency-calls/text'),
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: jsonEncode({
        'text': text.trim(),
        'language': _validatedLanguage(language),
        'latitude': latitude,
        'longitude': longitude,
        'location_accuracy': locationAccuracy,
        'location_timestamp': locationTimestamp?.toUtc().toIso8601String(),
        'source': 'flutter',
        if (clientMetadata != null) 'client_metadata': clientMetadata,
      }),
    );

    if (response.statusCode != 201) {
      throw ApiException(
        'Text emergency submission failed (${response.statusCode}): ${response.body}',
      );
    }

    final call = EmergencyCall.fromJson(
      jsonDecode(response.body) as Map<String, dynamic>,
    );
    debugPrint(
      '[EmergencyIQ] Saved text emergency id=${call.id} '
      'lat=${call.latitude} long=${call.longitude} status=${call.status}',
    );
    return call;
  }

  /// Preferred: store voice file and its matching text together.
  Future<EmergencyCall> submitVoiceAndText({
    required File audioFile,
    required String transcription,
    required String language,
    double? latitude,
    double? longitude,
    double? locationAccuracy,
    DateTime? locationTimestamp,
    Map<String, dynamic>? clientMetadata,
  }) async {
    final baseUrl = await ApiClient.getBaseUrl();
    final uri = Uri.parse('$baseUrl/api/v1/emergency-calls/voice-text');
    debugPrint('[EmergencyIQ] POST $uri');
    final request = http.MultipartRequest('POST', uri)
      ..fields['language'] = _validatedLanguage(language)
      ..fields['transcription'] = transcription.trim()
      ..fields['source'] = 'flutter';

    if (latitude != null) {
      request.fields['latitude'] = latitude.toString();
    }
    if (longitude != null) {
      request.fields['longitude'] = longitude.toString();
    }
    if (locationAccuracy != null) {
      request.fields['location_accuracy'] = locationAccuracy.toString();
    }
    if (locationTimestamp != null) {
      request.fields['location_timestamp'] = locationTimestamp.toUtc().toIso8601String();
    }
    if (clientMetadata != null) {
      request.fields['client_metadata'] = jsonEncode(clientMetadata);
    }

    request.files.add(
      await http.MultipartFile.fromPath(
        'file',
        audioFile.path,
        filename: audioFile.path.split(Platform.pathSeparator).last,
      ),
    );

    final streamedResponse = await request.send();
    final response = await http.Response.fromStream(streamedResponse);

    if (response.statusCode != 201) {
      throw ApiException(
        'Voice+text submission failed (${response.statusCode}): ${response.body}',
      );
    }

    final call = EmergencyCall.fromJson(
      jsonDecode(response.body) as Map<String, dynamic>,
    );
    debugPrint(
      '[EmergencyIQ] Saved voice+text emergency id=${call.id} '
      'lat=${call.latitude} long=${call.longitude} status=${call.status}',
    );
    return call;
  }

  /// Audio-only (transcription optional). Kept for backward compatibility.
  Future<EmergencyCall> submitAudioEmergency({
    required File audioFile,
    required String language,
    String? transcription,
    double? latitude,
    double? longitude,
    double? locationAccuracy,
    DateTime? locationTimestamp,
    Map<String, dynamic>? clientMetadata,
  }) async {
    final baseUrl = await ApiClient.getBaseUrl();
    final uri = Uri.parse('$baseUrl/api/v1/emergency-calls/audio');
    final request = http.MultipartRequest('POST', uri)
      ..fields['language'] = _validatedLanguage(language)
      ..fields['source'] = 'flutter';

    if (transcription != null && transcription.trim().isNotEmpty) {
      request.fields['transcription'] = transcription.trim();
    }
    if (latitude != null) {
      request.fields['latitude'] = latitude.toString();
    }
    if (longitude != null) {
      request.fields['longitude'] = longitude.toString();
    }
    if (locationAccuracy != null) {
      request.fields['location_accuracy'] = locationAccuracy.toString();
    }
    if (locationTimestamp != null) {
      request.fields['location_timestamp'] = locationTimestamp.toUtc().toIso8601String();
    }
    if (clientMetadata != null) {
      request.fields['client_metadata'] = jsonEncode(clientMetadata);
    }

    request.files.add(
      await http.MultipartFile.fromPath(
        'file',
        audioFile.path,
        filename: audioFile.path.split(Platform.pathSeparator).last,
      ),
    );

    final streamedResponse = await request.send();
    final response = await http.Response.fromStream(streamedResponse);

    if (response.statusCode != 201) {
      throw ApiException(
        'Audio emergency submission failed (${response.statusCode}): ${response.body}',
      );
    }

    final call = EmergencyCall.fromJson(
      jsonDecode(response.body) as Map<String, dynamic>,
    );
    debugPrint(
      '[EmergencyIQ] Saved audio emergency id=${call.id} '
      'lat=${call.latitude} long=${call.longitude} status=${call.status}',
    );
    return call;
  }

  Future<List<EmergencyCall>> listEmergencyCalls({
    int limit = 50,
    int offset = 0,
  }) async {
    final baseUrl = await ApiClient.getBaseUrl();
    final uri = Uri.parse(
      '$baseUrl/api/v1/emergency-calls/?limit=$limit&offset=$offset',
    );
    final response = await ApiClient.client.get(
      uri,
      headers: {'Accept': 'application/json'},
    );

    if (response.statusCode != 200) {
      throw ApiException(
        'Failed to list emergencies (${response.statusCode}): ${response.body}',
      );
    }

    final body = jsonDecode(response.body) as Map<String, dynamic>;
    final items = (body['items'] as List<dynamic>? ?? [])
        .map((e) => EmergencyCall.fromJson(e as Map<String, dynamic>))
        .toList();
    return items;
  }
}

class ApiException implements Exception {
  final String message;
  ApiException(this.message);

  @override
  String toString() => message;
}
