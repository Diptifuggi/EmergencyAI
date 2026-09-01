import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter/foundation.dart' show debugPrint;
import 'package:http/http.dart' as http;

import '../core/language/language_mapper.dart';
import '../core/network/api_client.dart';
import '../models/emergency_call.dart';

class EmergencyApiService {
  Future<void> _addMapSnapshot(
    http.MultipartRequest request,
    Uint8List? bytes,
  ) async {
    if (bytes == null || bytes.isEmpty) return;
    request.files.add(http.MultipartFile.fromBytes(
      'map_snapshot',
      bytes,
      filename: 'map_snapshot.png',
      contentType: http.MediaType('image', 'png'),
    ));
  }

  Future<EmergencyCall> attachMapSnapshot({
    required String callId,
    required Uint8List bytes,
  }) async {
    final baseUrl = await ApiClient.getBaseUrl();
    final request = http.MultipartRequest(
      'POST',
      Uri.parse('$baseUrl/api/v1/emergency-calls/$callId/map-snapshot'),
    )..files.add(http.MultipartFile.fromBytes(
        'map_snapshot',
        bytes,
        filename: 'map_snapshot.png',
        contentType: http.MediaType('image', 'png'),
      ));
    final response = await http.Response.fromStream(await request.send());
    if (response.statusCode != 200) {
      throw ApiException(
        'Map snapshot upload failed (${response.statusCode}): ${response.body}',
      );
    }
    return EmergencyCall.fromJson(
      jsonDecode(response.body) as Map<String, dynamic>,
    );
  }

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
    Uint8List? mapSnapshot,
    Uint8List? audioBytes,
  }) async {
    final baseUrl = await ApiClient.getBaseUrl();
    final uri = Uri.parse('$baseUrl/api/v1/emergency-calls/voice-text');
    debugPrint('[EmergencyIQ] POST $uri');
    final request = http.MultipartRequest('POST', uri)
      ..fields['language'] = _validatedLanguage(language)
      ..fields['transcription'] = transcription.trim()
      ..fields['source'] = 'flutter';
    await _addMapSnapshot(request, mapSnapshot);

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
      request.fields['location_timestamp'] =
          locationTimestamp.toUtc().toIso8601String();
    }
    if (clientMetadata != null) {
      request.fields['client_metadata'] = jsonEncode(clientMetadata);
    }

    final payload = audioBytes ?? await audioFile.readAsBytes();
    debugPrint(
      '[EmergencyIQ] Multipart field=file filename=${audioFile.path.split(Platform.pathSeparator).last} '
      'bytesSent=${payload.length} contentType=${_audioMediaType(audioFile.path)}',
    );
    request.files.add(
      http.MultipartFile.fromBytes(
        'file',
        payload,
        filename: audioFile.path.split(Platform.pathSeparator).last,
        contentType: _audioMediaType(audioFile.path),
      ),
    );

    final streamedResponse = await request.send();
    final response = await http.Response.fromStream(streamedResponse);
    debugPrint(
        '[EmergencyIQ] Multipart field=file filename=${audioFile.path.split(Platform.pathSeparator).last} responseStatus=${response.statusCode}');

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
    Uint8List? mapSnapshot,
    Uint8List? audioBytes,
  }) async {
    final baseUrl = await ApiClient.getBaseUrl();
    final uri = Uri.parse('$baseUrl/api/v1/emergency-calls/audio');
    final request = http.MultipartRequest('POST', uri)
      ..fields['language'] = _validatedLanguage(language)
      ..fields['source'] = 'flutter';
    await _addMapSnapshot(request, mapSnapshot);

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
      request.fields['location_timestamp'] =
          locationTimestamp.toUtc().toIso8601String();
    }
    if (clientMetadata != null) {
      request.fields['client_metadata'] = jsonEncode(clientMetadata);
    }

    final payload = audioBytes ?? await audioFile.readAsBytes();
    debugPrint(
      '[EmergencyIQ] Multipart field=file filename=${audioFile.path.split(Platform.pathSeparator).last} '
      'bytesSent=${payload.length} contentType=${_audioMediaType(audioFile.path)}',
    );
    request.files.add(
      http.MultipartFile.fromBytes(
        'file',
        payload,
        filename: audioFile.path.split(Platform.pathSeparator).last,
        contentType: _audioMediaType(audioFile.path),
      ),
    );

    final streamedResponse = await request.send();
    final response = await http.Response.fromStream(streamedResponse);
    debugPrint(
        '[EmergencyIQ] Multipart field=file filename=${audioFile.path.split(Platform.pathSeparator).last} responseStatus=${response.statusCode}');

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

  http.MediaType _audioMediaType(String filePath) {
    final extension = filePath.split('.').last.toLowerCase();
    switch (extension) {
      case 'm4a':
        return http.MediaType('audio', 'mp4');
      case 'mp3':
        return http.MediaType('audio', 'mpeg');
      case 'wav':
        return http.MediaType('audio', 'wav');
      case 'ogg':
        return http.MediaType('audio', 'ogg');
      case 'aac':
        return http.MediaType('audio', 'aac');
      default:
        return http.MediaType('application', 'octet-stream');
    }
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
