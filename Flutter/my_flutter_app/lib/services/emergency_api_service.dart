import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter/foundation.dart' show debugPrint, kDebugMode;
import 'package:http/http.dart' as http;

import '../core/language/language_mapper.dart';
import '../core/network/api_client.dart';
import '../core/network/api_config.dart';
import '../models/emergency_call.dart';

class EmergencyApiService {
  Uri _endpoint(String baseUrl, String path) => Uri.parse('$baseUrl$path');
  String _safePath(Uri uri) =>
      uri.path.replaceAll(RegExp(r'/[0-9a-fA-F-]{36}(?=/|$)'), '/{id}');

  void _log(String message) {
    if (kDebugMode) debugPrint('[API] $message');
  }

  Future<http.Response> _request(
    Future<http.Response> request, {
    required String method,
    required Uri uri,
  }) async {
    final stopwatch = Stopwatch()..start();
    final endpoint = _safePath(uri);
    _log('$method $endpoint request start');
    try {
      final response = await request.timeout(ApiConfig.requestTimeout);
      _log(
        '$method $endpoint response status=${response.statusCode} '
        'elapsed_ms=${stopwatch.elapsedMilliseconds}',
      );
      return response;
    } on TimeoutException catch (error) {
      _log(
        '$method $endpoint timeout type=${error.runtimeType} '
        'elapsed_ms=${stopwatch.elapsedMilliseconds}',
      );
      throw ApiException('Backend request timed out. Please try again.');
    } on SocketException catch (error) {
      _log(
        '$method $endpoint connection failure type=${error.runtimeType} '
        'elapsed_ms=${stopwatch.elapsedMilliseconds}',
      );
      throw ApiException('Cannot connect to EmergencyIQ backend.');
    } on http.ClientException catch (error) {
      _log(
        '$method $endpoint client failure type=${error.runtimeType} '
        'elapsed_ms=${stopwatch.elapsedMilliseconds}',
      );
      throw ApiException('Cannot connect to EmergencyIQ backend.');
    }
  }

  Future<http.Response> _sendMultipart(http.MultipartRequest request) async {
    final endpoint = _safePath(request.url);
    final stopwatch = Stopwatch()..start();
    var phase = 'send/upload/response-headers';
    _log('${request.method} $endpoint multipart request start');
    try {
      final streamed = await request.send().timeout(ApiConfig.uploadTimeout);
      phase = 'response-body';
      final response = await http.Response.fromStream(streamed)
          .timeout(ApiConfig.uploadTimeout);
      _log(
        '${request.method} $endpoint response status=${response.statusCode} '
        'elapsed_ms=${stopwatch.elapsedMilliseconds}',
      );
      return response;
    } on TimeoutException catch (error) {
      _log(
        '${request.method} $endpoint timeout phase=$phase '
        'type=${error.runtimeType} elapsed_ms=${stopwatch.elapsedMilliseconds}',
      );
      throw ApiException('Backend request timed out. Please try again.');
    } on SocketException catch (error) {
      _log(
        '${request.method} $endpoint connection failure phase=$phase '
        'type=${error.runtimeType} elapsed_ms=${stopwatch.elapsedMilliseconds}',
      );
      throw ApiException('Cannot connect to EmergencyIQ backend.');
    } on http.ClientException catch (error) {
      _log(
        '${request.method} $endpoint client failure phase=$phase '
        'type=${error.runtimeType} elapsed_ms=${stopwatch.elapsedMilliseconds}',
      );
      throw ApiException('Cannot connect to EmergencyIQ backend.');
    }
  }

  Future<Map<String, dynamic>> healthCheck() async {
    final baseUrl = await ApiClient.getBaseUrl();
    final uri = _endpoint(baseUrl, ApiConfig.healthEndpoint);
    final response = await _request(
      ApiClient.client.get(uri, headers: {'Accept': 'application/json'}),
      method: 'GET',
      uri: uri,
    );
    if (response.statusCode != 200) {
      throw ApiException(_backendError(
        response,
        'EmergencyIQ backend health check failed.',
      ));
    }
    final body = jsonDecode(response.body);
    if (body is! Map<String, dynamic>) {
      throw ApiException('EmergencyIQ backend returned an invalid health response.');
    }
    return body;
  }

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
      _endpoint(
        baseUrl,
        ApiConfig.mapSnapshotEndpoint.replaceAll('{callId}', callId),
      ),
    )..files.add(http.MultipartFile.fromBytes(
        'map_snapshot',
        bytes,
        filename: 'map_snapshot.png',
        contentType: http.MediaType('image', 'png'),
      ));
    final response = await _sendMultipart(request);
    if (response.statusCode != 200) {
      throw ApiException(
        _backendError(response, 'Unable to upload the map snapshot.'),
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
        'Invalid EmergencyIQ language "$language". Expected auto, en, hi, gu, or mr.',
      );
    }
    return canonical!;
  }

  Future<SarvamTranscription> transcribeAudio({
    required File audioFile,
    required String language,
    Uint8List? audioBytes,
  }) async {
    final baseUrl = await ApiClient.getBaseUrl();
    final uri = _endpoint(baseUrl, ApiConfig.sttEndpoint);
    final request = http.MultipartRequest(
      'POST',
      uri,
    )..fields['language_code'] = _sarvamLanguageCode(language);
    final payload = audioBytes ?? await audioFile.readAsBytes();
    if (payload.isEmpty) {
      throw ApiException('Audio recording is empty. Please record again.');
    }
    request.files.add(http.MultipartFile.fromBytes(
      'file',
      payload,
      filename: audioFile.path.split(Platform.pathSeparator).last,
      contentType: _audioMediaType(audioFile.path),
    ));
    _log('POST ${ApiConfig.sttEndpoint}');
    final response = await _sendMultipart(request);
    _log('Status: ${response.statusCode}');
    if (response.statusCode != 200) {
      throw ApiException(_backendError(response, 'Unable to transcribe audio. Please try again.'));
    }
    final body = jsonDecode(response.body) as Map<String, dynamic>;
    final result = SarvamTranscription.fromJson(body);
    if (result.transcript.trim().isEmpty) {
      throw ApiException('No speech was detected. Please record a clearer message.');
    }
    _log('Transcription completed.');
    return result;
  }

  String _sarvamLanguageCode(String language) {
    final canonical = LanguageMapper.toApiCode(language);
    switch (canonical) {
      case 'en-IN':
        return 'en-IN';
      case 'hi-IN':
        return 'hi-IN';
      case 'gu-IN':
        return 'gu-IN';
      case 'mr-IN':
        return 'mr-IN';
      case 'auto':
        return 'unknown';
      default:
        throw ApiException('Please select a supported transcription language.');
    }
  }

  String _backendError(http.Response response, String fallback) {
    if (response.statusCode == 401) {
      return 'Authentication is required to contact the EmergencyIQ backend.';
    }
    if (response.statusCode == 403) {
      return 'You do not have permission to perform this request.';
    }
    if (response.statusCode == 404) {
      return 'The requested EmergencyIQ endpoint was not found.';
    }
    if (response.statusCode >= 500) {
      return 'EmergencyIQ backend is unavailable. Please try again later.';
    }

    try {
      final body = jsonDecode(response.body) as Map<String, dynamic>;
      final detail = body['detail'];
      if (detail is String && detail.trim().isNotEmpty) return detail;
      if (detail is List) {
        final messages = detail.whereType<Map>().map((item) {
          final location = item['loc'];
          final field = location is List && location.isNotEmpty
              ? location.skip(1).join('.')
              : 'request';
          final message = item['msg']?.toString();
          return message == null || message.isEmpty ? null : '$field: $message';
        }).whereType<String>().toList();
        if (messages.isNotEmpty) return 'Invalid request: ${messages.join('; ')}';
      }
    } catch (_) {
      // Keep server internals and malformed responses out of the UI.
    }
    if (response.statusCode == 400) return 'The request is invalid. Please review it and try again.';
    if (response.statusCode == 422) return 'Some submitted information is invalid. Please review it and try again.';
    return fallback;
  }

  Future<EmergencyCall> submitTextEmergency({
    required String text,
    required String language,
    required String idempotencyKey,
    double? latitude,
    double? longitude,
    double? locationAccuracy,
    DateTime? locationTimestamp,
    Map<String, dynamic>? clientMetadata,
  }) async {
    final baseUrl = await ApiClient.getBaseUrl();
    final uri = _endpoint(baseUrl, ApiConfig.textEmergencyEndpoint);
    final response = await _request(
      ApiClient.client.post(
        uri,
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          'Idempotency-Key': idempotencyKey,
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
      ),
      method: 'POST',
      uri: uri,
    );

    if (response.statusCode != 201) {
      throw ApiException(_backendError(
        response,
        'Unable to submit the emergency message. Please try again.',
      ));
    }

    final call = EmergencyCall.fromJson(
      jsonDecode(response.body) as Map<String, dynamic>,
    );
    _log('Status: ${response.statusCode}; emergency id=${call.id}');
    return call;
  }

  /// Preferred: store voice file and its matching text together.
  Future<EmergencyCall> submitVoiceAndText({
    required File audioFile,
    required String transcription,
    required String language,
    required String idempotencyKey,
    double? latitude,
    double? longitude,
    double? locationAccuracy,
    DateTime? locationTimestamp,
    Map<String, dynamic>? clientMetadata,
    Uint8List? mapSnapshot,
    Uint8List? audioBytes,
  }) async {
    final baseUrl = await ApiClient.getBaseUrl();
    final uri = _endpoint(baseUrl, ApiConfig.voiceTextEmergencyEndpoint);
    _log('POST ${ApiConfig.voiceTextEmergencyEndpoint}');
    final request = http.MultipartRequest('POST', uri)
      ..fields['language'] = _validatedLanguage(language)
      ..fields['transcription'] = transcription.trim()
      ..fields['source'] = 'flutter'
      ..headers['Idempotency-Key'] = idempotencyKey;
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
    request.files.add(
      http.MultipartFile.fromBytes(
        'file',
        payload,
        filename: audioFile.path.split(Platform.pathSeparator).last,
        contentType: _audioMediaType(audioFile.path),
      ),
    );

    final response = await _sendMultipart(request);
    _log('Status: ${response.statusCode}');

    if (response.statusCode != 201) {
      throw ApiException(_backendError(
        response,
        'Unable to submit the voice emergency. Please try again.',
      ));
    }

    final call = EmergencyCall.fromJson(
      jsonDecode(response.body) as Map<String, dynamic>,
    );
    _log('Voice+text emergency saved; id=${call.id}');
    return call;
  }

  /// Audio-only (transcription optional). Kept for backward compatibility.
  Future<EmergencyCall> submitAudioEmergency({
    required File audioFile,
    required String language,
    required String idempotencyKey,
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
    final uri = _endpoint(baseUrl, ApiConfig.audioEmergencyEndpoint);
    _log('POST ${ApiConfig.audioEmergencyEndpoint}');
    final request = http.MultipartRequest('POST', uri)
      ..fields['language'] = _validatedLanguage(language)
      ..fields['source'] = 'flutter'
      ..headers['Idempotency-Key'] = idempotencyKey;
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
    request.files.add(
      http.MultipartFile.fromBytes(
        'file',
        payload,
        filename: audioFile.path.split(Platform.pathSeparator).last,
        contentType: _audioMediaType(audioFile.path),
      ),
    );

    final response = await _sendMultipart(request);
    _log('Status: ${response.statusCode}');

    if (response.statusCode != 201) {
      throw ApiException(_backendError(
        response,
        'Unable to submit the audio emergency. Please try again.',
      ));
    }

    final call = EmergencyCall.fromJson(
      jsonDecode(response.body) as Map<String, dynamic>,
    );
    _log('Audio emergency saved; id=${call.id}');
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
      '$baseUrl${ApiConfig.emergencyCallsEndpoint}/?limit=$limit&offset=$offset',
    );
    final response = await _request(
      ApiClient.client.get(uri, headers: {'Accept': 'application/json'}),
      method: 'GET',
      uri: uri,
    );

    if (response.statusCode != 200) {
      throw ApiException(_backendError(
        response,
        'Unable to load emergency reports. Please try again.',
      ));
    }

    final body = jsonDecode(response.body) as Map<String, dynamic>;
    final items = (body['items'] as List<dynamic>? ?? [])
        .map((e) => EmergencyCall.fromJson(e as Map<String, dynamic>))
        .toList();
    return items;
  }
}

class SarvamTranscription {
  const SarvamTranscription({
    required this.transcript,
    required this.language,
    required this.provider,
    required this.model,
    required this.timestamp,
    required this.metadata,
  });

  final String transcript;
  final String? language;
  final String provider;
  final String model;
  final String timestamp;
  final Map<String, dynamic> metadata;

  factory SarvamTranscription.fromJson(Map<String, dynamic> json) {
    return SarvamTranscription(
      transcript: (json['transcript'] as String? ?? '').trim(),
      language: json['language'] as String?,
      provider: json['provider'] as String? ?? 'sarvam',
      model: json['model'] as String? ?? 'unknown',
      timestamp: json['timestamp'] as String? ?? DateTime.now().toUtc().toIso8601String(),
      metadata: (json['metadata'] as Map?)?.cast<String, dynamic>() ?? const {},
    );
  }
}

class ApiException implements Exception {
  final String message;
  ApiException(this.message);

  @override
  String toString() => message;
}
