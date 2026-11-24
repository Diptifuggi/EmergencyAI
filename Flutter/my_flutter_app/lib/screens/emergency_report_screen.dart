import 'dart:async';
import 'dart:io';
import 'dart:math';
import 'dart:typed_data';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter/foundation.dart' show debugPrint, kIsWeb;
import 'package:flutter/material.dart';
import 'package:path/path.dart' as path;
import 'package:path_provider/path_provider.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:record/record.dart';

import '../core/language/emergency_language_option.dart';
import '../core/language/language_mapper.dart';
import '../core/network/api_client.dart';
import '../core/network/api_config.dart';
import '../models/emergency_call.dart';
import '../models/emergency_location.dart';
import '../services/emergency_api_service.dart';
import '../services/location_service.dart';
import '../widgets/app_colors.dart';
import '../widgets/emergency_location_card.dart';
import 'map_screen.dart';

class EmergencyReportScreen extends StatefulWidget {
  const EmergencyReportScreen({super.key});

  @override
  State<EmergencyReportScreen> createState() => _EmergencyReportScreenState();
}

class _EmergencyReportScreenState extends State<EmergencyReportScreen> {
  final _textController = TextEditingController();
  final _latitudeController = TextEditingController();
  final _longitudeController = TextEditingController();
  final _record = AudioRecorder();
  final _locationService = LocationService();

  EmergencyLanguageOption _selectedLanguage = EmergencyLanguageOption.english;

  bool _isRecording = false;
  bool _isSarvamRecording = false;
  bool _isSubmitting = false;
  bool _isTranscribing = false;
  bool _isRefreshingAnalysis = false;
  String? _audioPath;
  String? _transcriptionLanguage;
  Map<String, dynamic>? _transcriptionMetadata;
  String? _statusMessage;
  String? _backendUrl;
  bool _isDiscoveringBackend = false;
  bool _isBackendConnected = false;
  String? _pendingTextSubmissionKey;
  String? _pendingVoiceSubmissionKey;
  StreamSubscription<List<ConnectivityResult>>? _connectivitySub;
  EmergencyLocation? _currentLocation;
  EmergencyCall? _lastSavedCall;
  String? _locationError;
  Uint8List? _mapSnapshot;
  String _mapSnapshotStatus = 'Map snapshot not captured';

  @override
  void initState() {
    super.initState();
    _textController.addListener(_invalidateSubmissionKeys);
    _initBackendConnection();
  }

  @override
  void dispose() {
    _connectivitySub?.cancel();
    _textController.removeListener(_invalidateSubmissionKeys);
    _textController.dispose();
    _longitudeController.dispose();
    _latitudeController.dispose();
    _record.dispose();
    super.dispose();
  }

  void _invalidateSubmissionKeys() {
    _pendingTextSubmissionKey = null;
    _pendingVoiceSubmissionKey = null;
  }

  String _newIdempotencyKey() {
    final random = Random.secure();
    return List<int>.generate(16, (_) => random.nextInt(256))
        .map((byte) => byte.toRadixString(16).padLeft(2, '0'))
        .join();
  }

  Future<void> _initBackendConnection() async {
    await _checkBackendConnection();

    _connectivitySub =
        Connectivity().onConnectivityChanged.listen((results) async {
      final onWifi = results.contains(ConnectivityResult.wifi) ||
          results.contains(ConnectivityResult.ethernet);
      if (onWifi && mounted) {
        await _checkBackendConnection(refresh: true);
      }
    });
  }

  Future<void> _checkBackendConnection({bool refresh = false}) async {
    if (!mounted || _isDiscoveringBackend) return;
    setState(() => _isDiscoveringBackend = true);
    try {
      if (!kIsWeb && Platform.environment.containsKey('FLUTTER_TEST')) {
        final url = await ApiClient.getBaseUrl();
        if (!mounted) return;
        setState(() {
          _backendUrl = url;
          _isBackendConnected = false;
        });
        return;
      }

      final url = refresh
          ? await ApiClient.refreshBaseUrl()
          : await ApiClient.getBaseUrl();
      await EmergencyApiService().healthCheck();
      if (!mounted) return;
      setState(() {
        _backendUrl = url;
        _isBackendConnected = true;
      });
    } on ApiException catch (error) {
      debugPrint('[EmergencyIQ] Backend health check failed: $error');
      if (!mounted) return;
      setState(() {
        _backendUrl = ApiClient.baseUrl;
        _isBackendConnected = false;
      });
    } catch (error) {
      debugPrint(
        '[EmergencyIQ] Backend discovery failed (${error.runtimeType}).',
      );
      if (!mounted) return;
      setState(() {
        _backendUrl = ApiClient.baseUrl;
        _isBackendConnected = false;
      });
    } finally {
      if (mounted) setState(() => _isDiscoveringBackend = false);
    }
  }

  String _formatSavedCall(EmergencyCall call) {
    final shortId =
        call.id.length > 8 ? '${call.id.substring(0, 8)}…' : call.id;
    final lat = call.latitude?.toString() ?? 'not set';
    final long = call.longitude?.toString() ?? 'not set';
    final accuracy = call.locationAccuracy == null
        ? ''
        : ' Accuracy: ${call.locationAccuracy!.toStringAsFixed(1)}m.';
    return 'Saved (id: $shortId). Lat: $lat, Long: $long.$accuracy Status: ${call.status}.';
  }

  Future<void> _pollForEmergencyAnalysis(String callId) async {
    if (_isRefreshingAnalysis) return;
    setState(() => _isRefreshingAnalysis = true);
    final stopwatch = Stopwatch()..start();
    var interval = ApiConfig.analysisPollInterval;

    try {
      while (mounted && stopwatch.elapsed < ApiConfig.analysisPollTimeout) {
        await Future<void>.delayed(interval);
        if (!mounted) return;

        final updatedCall =
            await EmergencyApiService().getEmergencyCall(callId: callId);
        if (!mounted) return;

        setState(() {
          _lastSavedCall = updatedCall;
          if (updatedCall.status == 'analyzed') {
            _statusMessage =
                'Emergency analysis complete. ${_formatSavedCall(updatedCall)}';
          } else if (updatedCall.status == 'analysis_failed') {
            _statusMessage =
                'Emergency analysis could not be completed. ${_formatSavedCall(updatedCall)}';
          } else {
            _statusMessage =
                'Emergency analysis is still running. ${_formatSavedCall(updatedCall)}';
          }
        });

        if (updatedCall.status != 'analyzing') return;
        interval = Duration(seconds: min(interval.inSeconds + 1, 6));
      }

      if (mounted) {
        setState(() {
          _statusMessage =
              'Analysis is still processing. Use Refresh analysis to check again.';
        });
      }
    } on ApiException {
      if (mounted) {
        setState(() {
          _statusMessage =
              'Could not refresh analysis status. Use Refresh analysis to try again.';
        });
      }
    } finally {
      if (mounted) setState(() => _isRefreshingAnalysis = false);
    }
  }

  Future<EmergencyLocation?> _locationForSubmission() async {
    try {
      final location = await _locationService.getCurrentLocation();
      if (!mounted) return location;
      setState(() {
        _currentLocation = location;
        _locationError = null;
        _latitudeController.text = location.latitude.toStringAsFixed(7);
        _longitudeController.text = location.longitude.toStringAsFixed(7);
        _statusMessage =
            'GPS location captured (±${location.accuracy.toStringAsFixed(1)} m).';
      });
      return location;
    } catch (error) {
      if (mounted) {
        setState(() {
          _clearLocationDraft();
          _locationError = error.toString();
          _statusMessage =
              'GPS unavailable; submitting without live location. $error';
        });
      }
      return null;
    }
  }

  void _clearLocationDraft() {
    _currentLocation = null;
    _latitudeController.clear();
    _longitudeController.clear();
    _mapSnapshot = null;
    _mapSnapshotStatus = 'Map snapshot not captured';
    _locationError = null;
  }

  void _onLanguageChanged(EmergencyLanguageOption? value) {
    if (value == null) return;
    setState(() {
      _selectedLanguage = value;
    });
    _logLanguageContext();
  }

  String? _resolveApiLanguage() {
    return LanguageMapper.resolveApiCode(selected: _selectedLanguage);
  }

  String? _canonicalLanguage(String? value) {
    return LanguageMapper.toApiCode(value);
  }

  void _logLanguageContext() {
    final apiLanguage = _resolveApiLanguage();
    debugPrint('[LANG] UI selection=${_selectedLanguage.displayName}');
    debugPrint('[LANG] request language=${apiLanguage ?? 'invalid'}');
  }

  Future<void> _startSarvamRecording() async {
    if (kIsWeb) {
      _showMessage('Speech recognition is not supported on Web.');
      return;
    }
    try {
      setState(() => _isSarvamRecording = true);
      await _startRecording();
      if (mounted && !_isRecording) {
        setState(() => _isSarvamRecording = false);
      }
    } catch (_) {
      if (mounted) {
        setState(() => _isSarvamRecording = false);
        _showMessage('Unable to start microphone recording. Please try again.');
      }
    }
  }

  Future<void> _stopSarvamRecording() async {
    try {
      await _stopRecording();
      if (!mounted || _audioPath == null) return;
      await _transcribeRecordedAudio();
    } catch (_) {
      if (mounted) {
        _showMessage('Unable to record audio. Please try again.');
      }
    } finally {
      if (mounted) setState(() => _isSarvamRecording = false);
    }
  }

  Future<void> _transcribeRecordedAudio() async {
    final audioPath = _audioPath;
    if (audioPath == null) return;
    final file = File(audioPath);
    if (!await file.exists() || await file.length() == 0) {
      _showMessage('Audio recording is empty. Please try again.');
      return;
    }

    final language = _resolveApiLanguage();
    if (!LanguageMapper.isValidApiCode(language)) {
      _showMessage('Please select a supported transcription language.');
      return;
    }

    setState(() {
      _isTranscribing = true;
      _statusMessage = 'Uploading audio and transcribing…';
    });
    try {
      final result = await EmergencyApiService().transcribeAudio(
        audioFile: file,
        language: language!,
      );
      _textController.text = result.transcript;
      _transcriptionLanguage = _canonicalLanguage(result.language) ??
          (language == 'auto' ? null : language);
      _transcriptionMetadata = {
        'stt_provider': result.provider,
        'stt_model': result.model,
        'stt_timestamp': result.timestamp,
        'stt_language': result.language,
        'stt_metadata': result.metadata,
      };
      debugPrint('[LANG] detected language=${result.language ?? 'unknown'}');
      _showMessage('Speech converted successfully');
    } catch (error) {
      _showMessage(_friendlyError(error));
    } finally {
      if (mounted) setState(() => _isTranscribing = false);
    }
  }

  Future<void> _startRecording() async {
    if (kIsWeb) {
      _showMessage('Audio recording is not supported on Web.');
      return;
    }

    final permission = await Permission.microphone.request();
    if (!permission.isGranted) {
      _showMessage('Microphone permission is required to record audio.');
      return;
    }

    final hasPermission = await _record.hasPermission();
    if (!hasPermission) {
      _showMessage('Microphone permission is required to record audio.');
      return;
    }

    final tempDir = await getTemporaryDirectory();
    _pendingVoiceSubmissionKey = null;
    final fileName = 'emergency_${DateTime.now().millisecondsSinceEpoch}.m4a';
    final filePath = path.join(tempDir.path, fileName);

    await _record.start(
      const RecordConfig(
        encoder: AudioEncoder.aacLc,
        bitRate: 128000,
        sampleRate: 44100,
      ),
      path: filePath,
    );

    debugPrint('[EmergencyIQ] Recording started format=m4a mime=audio/mp4');

    setState(() {
      _isRecording = true;
      _audioPath = filePath;
      _statusMessage = 'Recording audio...';
    });
  }

  Future<void> _stopRecording() async {
    if (!_isRecording) return;

    final savedPath = await _record.stop();
    final resolvedPath = savedPath ?? _audioPath;
    final exists = resolvedPath != null && await File(resolvedPath).exists();
    final size =
        resolvedPath == null || !exists ? 0 : await File(resolvedPath).length();
    debugPrint(
      '[EmergencyIQ] Recording stopped exists=$exists sizeBytes=$size '
      'extension=${resolvedPath == null ? 'unknown' : path.extension(resolvedPath)}',
    );
    setState(() {
      _isRecording = false;
      _audioPath = resolvedPath;
      _statusMessage = _audioPath == null
          ? 'Audio recording stopped, but no file was created.'
          : size <= 0
              ? 'Audio recording is empty or could not be captured. Please record again.'
              : 'Audio saved to ${path.basename(_audioPath!)} ($size bytes)';
    });
  }

  Future<void> _submitTextEmergency() async {
    final text = _textController.text.trim();
    final language = _resolveApiLanguage();

    if (text.isEmpty) {
      _showMessage('Please enter or speak an emergency message.');
      return;
    }

    if (!LanguageMapper.isValidApiCode(language)) {
      _showMessage(
        'Could not determine a valid EmergencyIQ language. Please select English, Hindi, Gujarati, or Marathi.',
      );
      return;
    }

    _logLanguageContext();

    setState(() => _isSubmitting = true);
    try {
      final location = await _locationForSubmission();
      final idempotencyKey =
          _pendingTextSubmissionKey ??= _newIdempotencyKey();
      final call = await EmergencyApiService().submitTextEmergency(
        text: text,
        language: language!,
        idempotencyKey: idempotencyKey,
        latitude:
            location?.latitude ?? _parseCoordinate(_latitudeController.text),
        longitude:
            location?.longitude ?? _parseCoordinate(_longitudeController.text),
        locationAccuracy: location?.accuracy ?? _currentLocation?.accuracy,
        locationTimestamp: location?.timestamp ?? _currentLocation?.timestamp,
        clientMetadata: {
          'platform': 'flutter',
          'map_snapshot_status': _mapSnapshotStatus,
          if (_locationError != null) 'location_error': _locationError,
        },
      );
      _lastSavedCall = call;
      if (_mapSnapshot != null) {
        try {
          _lastSavedCall = await EmergencyApiService().attachMapSnapshot(
            callId: call.id,
            bytes: _mapSnapshot!,
          );
          _mapSnapshotStatus = 'Map snapshot stored with incident';
        } catch (error) {
          _mapSnapshotStatus = 'Map snapshot unavailable: ${_friendlyError(error)}';
        }
      }
      final savedCall = _lastSavedCall ?? call;
      final snapshotFailure = _mapSnapshotStatus.startsWith('Map snapshot unavailable:')
          ? _mapSnapshotStatus
          : null;
      setState(_clearLocationDraft);
      if (savedCall.status == 'analyzing') {
        _showMessage(
          '${_formatSavedCall(savedCall)} Analysis is running; checking for the completed result.'
          '${snapshotFailure == null ? '' : ' $snapshotFailure'}',
        );
        unawaited(_pollForEmergencyAnalysis(savedCall.id));
      } else {
        _showMessage(
          '${_formatSavedCall(savedCall)}'
          '${snapshotFailure == null ? '' : ' $snapshotFailure'}',
        );
      }
      _textController.clear();
    } catch (error) {
      _showMessage(_friendlyError(error));
    } finally {
      setState(() => _isSubmitting = false);
    }
  }

  Future<void> _submitAudioEmergency() async {
    if (_audioPath == null) {
      _showMessage('Please record audio first.');
      return;
    }

    final file = File(_audioPath!);
    if (!await file.exists()) {
      _showMessage('Audio file is missing. Please record again.');
      return;
    }
    final fileSize = await file.length();
    if (fileSize <= 0) {
      _showMessage(
          'Audio recording is empty or could not be captured. Please record again.');
      return;
    }
    final audioBytes = await file.readAsBytes();
    debugPrint(
      '[EmergencyIQ] Upload preparation sizeBytes=$fileSize '
      'bytesRead=${audioBytes.length} '
      'extension=${path.extension(file.path)} mime=audio/mp4 multipartField=file '
    );

    var transcription = _textController.text.trim();
    final language = _resolveApiLanguage();

    if (!LanguageMapper.isValidApiCode(language)) {
      _showMessage(
        'Could not determine a valid EmergencyIQ language. Please select English, Hindi, Gujarati, or Marathi.',
      );
      return;
    }

    _logLanguageContext();

    // A blank review field means the user has not yet received a Sarvam transcript.
    // Transcribe first and stop here so the user can review/edit before submission.
    if (transcription.isEmpty) {
      try {
        setState(() {
          _isTranscribing = true;
          _statusMessage = 'Uploading audio and transcribing…';
        });
        final transcriptionResult = await EmergencyApiService().transcribeAudio(
          audioFile: file,
          language: language!,
          audioBytes: audioBytes,
        );
        transcription = transcriptionResult.transcript;
        _textController.text = transcription;
        final detectedLanguage = _canonicalLanguage(transcriptionResult.language);
        _transcriptionLanguage = detectedLanguage;
        _transcriptionMetadata = {
          'stt_provider': transcriptionResult.provider,
          'stt_model': transcriptionResult.model,
          'stt_timestamp': transcriptionResult.timestamp,
          'stt_language': transcriptionResult.language,
          'stt_metadata': transcriptionResult.metadata,
        };
        if (_selectedLanguage == EmergencyLanguageOption.auto && detectedLanguage != null) {
          _statusMessage = 'Transcript ready (${transcriptionResult.language}). Review it, then submit again.';
        } else {
          _statusMessage = 'Transcript ready. Review it, then submit again.';
        }
        return;
      } catch (error) {
        _showMessage(_friendlyError(error));
        return;
      } finally {
        if (mounted) setState(() => _isTranscribing = false);
      }
    }

    final submissionLanguage = language == 'auto' ? _transcriptionLanguage : language;
    if (!LanguageMapper.isValidApiCode(submissionLanguage) || submissionLanguage == 'auto') {
      _showMessage('Please transcribe the recording with Sarvam before submitting.');
      return;
    }

    setState(() => _isSubmitting = true);
    try {
      final location = await _locationForSubmission();
      final service = EmergencyApiService();
      if (transcription.isNotEmpty) {
        final idempotencyKey =
            _pendingVoiceSubmissionKey ??= _newIdempotencyKey();
        final call = await service.submitVoiceAndText(
          audioFile: file,
          transcription: transcription,
          language: submissionLanguage!,
          idempotencyKey: idempotencyKey,
          latitude:
              location?.latitude ?? _parseCoordinate(_latitudeController.text),
          longitude: location?.longitude ??
              _parseCoordinate(_longitudeController.text),
          locationAccuracy: location?.accuracy ?? _currentLocation?.accuracy,
          locationTimestamp: location?.timestamp ?? _currentLocation?.timestamp,
          clientMetadata: {
            'platform': 'flutter',
            'map_snapshot_status': _mapSnapshotStatus,
            'recorded_at': DateTime.now().toIso8601String(),
            'selected_language': _selectedLanguage.displayName,
            if (_transcriptionMetadata != null) ..._transcriptionMetadata!,
            if (_locationError != null) 'location_error': _locationError,
          },
          mapSnapshot: _mapSnapshot,
          audioBytes: audioBytes,
        );
        _lastSavedCall = call;
        _showMessage(_formatSavedCall(call));
        _textController.clear();
      } else {
        final idempotencyKey =
            _pendingVoiceSubmissionKey ??= _newIdempotencyKey();
        final call = await service.submitAudioEmergency(
          audioFile: file,
          language: submissionLanguage!,
          idempotencyKey: idempotencyKey,
          latitude:
              location?.latitude ?? _parseCoordinate(_latitudeController.text),
          longitude: location?.longitude ??
              _parseCoordinate(_longitudeController.text),
          locationAccuracy: location?.accuracy ?? _currentLocation?.accuracy,
          locationTimestamp: location?.timestamp ?? _currentLocation?.timestamp,
          clientMetadata: {
            'platform': 'flutter',
            'map_snapshot_status': _mapSnapshotStatus,
            'recorded_at': DateTime.now().toIso8601String(),
            'selected_language': _selectedLanguage.displayName,
            if (_locationError != null) 'location_error': _locationError,
          },
          mapSnapshot: _mapSnapshot,
          audioBytes: audioBytes,
        );
        _lastSavedCall = call;
        _showMessage(
          '${_formatSavedCall(call)} Add text next time for full voice+text storage.',
        );
      }
      setState(() {
        _audioPath = null;
        _transcriptionLanguage = null;
        _transcriptionMetadata = null;
        _clearLocationDraft();
      });
    } catch (error) {
      _showMessage(_friendlyError(error));
    } finally {
      setState(() => _isSubmitting = false);
    }
  }

  double? _parseCoordinate(String value) {
    if (value.trim().isEmpty) return null;
    return double.tryParse(value.trim());
  }

  void _showMessage(String message) {
    setState(() => _statusMessage = message);
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message), duration: const Duration(seconds: 2)),
    );
  }

  String _friendlyError(Object error) {
    if (error is TimeoutException) {
      return 'Backend request timed out. Please try again.';
    }
    if (error is SocketException) {
      return 'Unable to connect to the EmergencyIQ server.';
    }
    final message = error.toString().replaceFirst('Exception: ', '').trim();
    return message.isEmpty
        ? 'The request failed. Please try again.'
        : message;
  }

  Future<void> _openCallerLocation() async {
    final snapshot = await Navigator.of(context).push<Uint8List>(
      MaterialPageRoute(
        builder: (context) => MapScreen(
          initialLocation: _currentLocation,
          title: 'Caller Location',
        ),
      ),
    );
    if (!mounted) return;
    setState(() {
      if (snapshot == null || snapshot.isEmpty) {
        _mapSnapshotStatus = 'Unable to capture map';
      } else {
        _mapSnapshot = snapshot;
        _mapSnapshotStatus = 'Map snapshot available';
      }
    });
  }

  Widget _buildLocationPreview() {
    final location = _currentLocation;
    if (location == null) return const SizedBox.shrink();
    return Card(
      color: AppColors.cardBackground,
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text('Emergency location',
                style: TextStyle(fontWeight: FontWeight.w700)),
            const SizedBox(height: 8),
            const Text('Location status: captured'),
            const SizedBox(height: 8),
            SizedBox(
              height: 220,
              child: ClipRRect(
                borderRadius: BorderRadius.circular(10),
                child: _mapSnapshot == null
                    ? Container(
                        color: Colors.grey.shade200,
                        alignment: Alignment.center,
                        child: Text(_mapSnapshotStatus),
                      )
                    : Image.memory(_mapSnapshot!, fit: BoxFit.cover),
              ),
            ),
            const SizedBox(height: 8),
            Text(
                'Latitude: ${location.latitude}\nLongitude: ${location.longitude}'),
            Text('GPS accuracy: ${location.accuracy.toStringAsFixed(1)} m'),
            Text(_mapSnapshotStatus),
          ],
        ),
      ),
    );
  }

  Widget _buildTextField({
    required String label,
    required TextEditingController controller,
    TextInputType keyboardType = TextInputType.text,
    bool readOnly = false,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: const TextStyle(fontWeight: FontWeight.w600)),
        const SizedBox(height: 8),
        TextField(
          controller: controller,
          keyboardType: keyboardType,
          readOnly: readOnly,
          maxLines: keyboardType == TextInputType.multiline ? 5 : 1,
          decoration: InputDecoration(
            filled: true,
            fillColor: AppColors.cardBackground,
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(14),
              borderSide: BorderSide(color: AppColors.border),
            ),
            contentPadding: const EdgeInsets.all(14),
          ),
        ),
      ],
    );
  }

  Widget _buildLanguageSelector() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('Language', style: TextStyle(fontWeight: FontWeight.w600)),
        const SizedBox(height: 8),
        DropdownButtonFormField<EmergencyLanguageOption>(
          value: _selectedLanguage,
          decoration: InputDecoration(
            filled: true,
            fillColor: AppColors.cardBackground,
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(14),
              borderSide: BorderSide(color: AppColors.border),
            ),
            contentPadding:
                const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
          ),
          items: EmergencyLanguageOption.all
              .map(
                (option) => DropdownMenuItem<EmergencyLanguageOption>(
                  value: option,
                  child: Text(option.displayName),
                ),
              )
              .toList(),
          onChanged: _isSubmitting ? null : _onLanguageChanged,
        ),
      ],
    );
  }

  Widget _buildBackendBanner() {
    final status = _isDiscoveringBackend
        ? 'Checking backend connection…'
        : _isBackendConnected
            ? 'Backend connected'
            : 'Backend unavailable — tap to retry';
    return InkWell(
      onTap: _isDiscoveringBackend
          ? null
          : () => unawaited(_checkBackendConnection(refresh: true)),
      borderRadius: BorderRadius.circular(12),
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        decoration: BoxDecoration(
          color: AppColors.cardBackground,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AppColors.border),
        ),
        child: Row(
          children: [
            Icon(
              _isDiscoveringBackend
                  ? Icons.sync
                  : _isBackendConnected
                      ? Icons.cloud_done_outlined
                      : Icons.cloud_off_outlined,
              size: 18,
              color: _isBackendConnected
                  ? AppColors.primary
                  : AppColors.secondaryText,
            ),
            const SizedBox(width: 8),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    status,
                    style: const TextStyle(
                      fontSize: 12,
                      color: AppColors.secondaryText,
                    ),
                  ),
                  if (_backendUrl != null)
                    Text(
                      _backendUrl!,
                      style: const TextStyle(
                        fontSize: 11,
                        color: AppColors.secondaryText,
                      ),
                    ),
                ],
              ),
            ),
            if (!_isDiscoveringBackend)
              const Icon(Icons.refresh,
                  size: 18, color: AppColors.secondaryText),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Emergency Report'),
        backgroundColor: AppColors.background,
        foregroundColor: AppColors.primaryText,
        elevation: 0,
      ),
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              _buildBackendBanner(),
              const SizedBox(height: 14),
              _buildLanguageSelector(),
              const SizedBox(height: 14),
              _buildTextField(
                label: 'Emergency text message',
                controller: _textController,
                keyboardType: TextInputType.multiline,
              ),
              if (!kIsWeb) ...[
                const SizedBox(height: 12),
                ElevatedButton.icon(
                    icon: Icon(_isSarvamRecording
                      ? Icons.stop_circle_outlined
                      : Icons.mic_none),
                    label: Text(_isSarvamRecording
                      ? 'Stop Listening'
                      : 'Speak Emergency (STT)'),
                    onPressed: _isSubmitting || _isTranscribing
                      ? null
                      : _isSarvamRecording
                        ? _stopSarvamRecording
                        : _startSarvamRecording,
                  style: ElevatedButton.styleFrom(
                    backgroundColor:
                      _isSarvamRecording ? AppColors.dangerRed : AppColors.primary,
                    padding: const EdgeInsets.symmetric(vertical: 14),
                  ),
                ),
              ],
              const SizedBox(height: 14),
              Row(
                children: [
                  Expanded(
                    child: _buildTextField(
                      label: 'Latitude',
                      controller: _latitudeController,
                      keyboardType: TextInputType.number,
                      readOnly: true,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: _buildTextField(
                      label: 'Longitude',
                      controller: _longitudeController,
                      keyboardType: TextInputType.number,
                      readOnly: true,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 10),
              OutlinedButton.icon(
                icon: const Icon(Icons.my_location),
                label: const Text('Capture current GPS location'),
                onPressed: _isSubmitting
                    ? null
                    : () async {
                        await _locationForSubmission();
                      },
              ),
              const SizedBox(height: 10),
              if (_currentLocation != null)
                ElevatedButton.icon(
                  icon: const Icon(Icons.map),
                  label: const Text('View location on map'),
                  onPressed: _isSubmitting
                      ? null
                      : () {
                          _openCallerLocation();
                        },
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppColors.primary,
                    padding: const EdgeInsets.symmetric(vertical: 14),
                  ),
                ),
              const SizedBox(height: 20),
              _buildLocationPreview(),
              const SizedBox(height: 4),
              ElevatedButton.icon(
                icon: const Icon(Icons.send_rounded),
                label: const Text('Submit Text Emergency'),
                onPressed: _isSubmitting ? null : _submitTextEmergency,
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.primary,
                  padding: const EdgeInsets.symmetric(vertical: 16),
                ),
              ),
              const SizedBox(height: 32),
              Text(
                'Voice / Audio Report',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w700,
                    ),
              ),
              const SizedBox(height: 12),
              if (kIsWeb)
                const Text(
                  'Audio recording is disabled on Web. Use native Android or iOS to submit voice emergencies.',
                  style: TextStyle(color: Colors.orangeAccent),
                ),
              if (!kIsWeb) ...[
                Row(
                  children: [
                    Expanded(
                      child: ElevatedButton.icon(
                        icon: Icon(_isRecording
                            ? Icons.stop_rounded
                            : Icons.mic_rounded),
                        label: Text(_isRecording
                            ? 'Stop Recording'
                            : 'Start Recording'),
                        onPressed: _isSubmitting || _isSarvamRecording || _isTranscribing
                            ? null
                            : _isRecording
                                ? _stopRecording
                                : _startRecording,
                        style: ElevatedButton.styleFrom(
                          backgroundColor: _isRecording
                              ? AppColors.dangerRed
                              : AppColors.primary,
                          padding: const EdgeInsets.symmetric(vertical: 16),
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                if (_audioPath != null)
                  Text(
                    'Recorded file: ${path.basename(_audioPath!)}',
                    style: const TextStyle(fontSize: 14),
                  ),
                const SizedBox(height: 16),
                ElevatedButton.icon(
                  icon: const Icon(Icons.upload_file_rounded),
                  label: const Text('Submit Voice + Text'),
                  onPressed: _isSubmitting || _isTranscribing ? null : _submitAudioEmergency,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppColors.secondaryText,
                    foregroundColor: AppColors.primaryText,
                    padding: const EdgeInsets.symmetric(vertical: 16),
                  ),
                ),
                const SizedBox(height: 8),
                const Text(
                  'Record audio, submit once to transcribe with Sarvam, review the transcript, then submit again.',
                  style: TextStyle(fontSize: 12),
                ),
              ],
              const SizedBox(height: 18),
              if (_statusMessage != null)
                Text(
                  _statusMessage!,
                  style: TextStyle(
                    color: AppColors.secondaryText,
                    fontSize: 14,
                  ),
                ),
              if (_lastSavedCall != null) ...[
                const SizedBox(height: 18),
                if (_lastSavedCall!.status == 'analyzing')
                  Align(
                    alignment: Alignment.centerRight,
                    child: TextButton.icon(
                      onPressed: _isRefreshingAnalysis
                          ? null
                          : () => unawaited(
                                _pollForEmergencyAnalysis(_lastSavedCall!.id),
                              ),
                      icon: const Icon(Icons.refresh),
                      label: Text(
                        _isRefreshingAnalysis
                            ? 'Checking analysis…'
                            : 'Refresh analysis',
                      ),
                    ),
                  ),
                EmergencyLocationCard(
                  call: _lastSavedCall!,
                  mapSnapshot: _mapSnapshot,
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
