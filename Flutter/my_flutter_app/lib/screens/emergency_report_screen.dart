import 'dart:async';
import 'dart:io';
import 'dart:math';
import 'dart:typed_data';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter/foundation.dart' show debugPrint, kIsWeb;
import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import 'package:path/path.dart' as path;
import 'package:path_provider/path_provider.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:record/record.dart';
import 'package:url_launcher/url_launcher.dart';

import '../core/constants/emergency_services.dart';
import '../core/language/emergency_language_option.dart';
import '../core/language/language_mapper.dart';
import '../core/network/api_client.dart';
import '../core/network/api_config.dart';
import '../l10n/app_localizations.dart';
import '../models/emergency_call.dart';
import '../models/emergency_location.dart';
import '../services/emergency_api_service.dart';
import '../services/home_feature_api_service.dart';
import '../services/location_service.dart';
import '../widgets/app_colors.dart';
import '../widgets/emergency_drawer.dart';
import '../widgets/emergency_location_card.dart';
import '../widgets/service_sos_bottom_sheet.dart';
import '../services/auth_storage_service.dart';
import '../services/sos_location_service.dart';
import 'about_us_screen.dart';
import 'edit_profile_screen.dart';
import 'location_permission_dialog.dart';
import 'login_screen.dart';
import 'notifications_screen.dart';
import 'sos_history_screen.dart';
import 'sos_screen.dart';
import 'map_screen.dart';
import 'track_me_screen.dart';


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
  bool _profileBannerDismissed = false;
  bool _profileCompleted = true;

  // 112-style Home Screen state
  final ScrollController _scrollController = ScrollController();
  final GlobalKey _textBoxKey = GlobalKey();
  int _unreadNotifications = 0;
  Timer? _notifPollTimer;
  String? _resolvedAddress;
  bool _isResolvingAddress = false;
  bool _locationOff = false;

  @override
  void initState() {
    super.initState();
    _textController.addListener(_invalidateSubmissionKeys);
    _initBackendConnection();
    _checkInitialState();
    _refreshUnreadCount();
    _notifPollTimer = Timer.periodic(const Duration(seconds: 15), (_) => _refreshUnreadCount());
    _refreshHomeLocationBar();
  }

  Future<void> _refreshUnreadCount() async {
    final count = await HomeFeatureApiService.getUnreadNotificationCount();
    if (mounted) {
      setState(() => _unreadNotifications = count);
    }
  }

  Future<void> _refreshHomeLocationBar() async {
    final cached = await HomeFeatureApiService.getCachedAddress();
    if (mounted && cached != null && _resolvedAddress == null) {
      setState(() => _resolvedAddress = cached);
    }

    final perm = await SosLocationService.checkPermission();
    final enabled = await Geolocator.isLocationServiceEnabled();
    if (!enabled || perm == LocationPermission.denied || perm == LocationPermission.deniedForever) {
      if (mounted) setState(() => _locationOff = true);
      return;
    }

    if (mounted) {
      setState(() {
        _locationOff = false;
        _isResolvingAddress = true;
      });
    }

    final fix = await SosLocationService.captureLocation(promptIfDenied: false);
    if (fix.latitude != null && fix.longitude != null) {
      final addr = await HomeFeatureApiService.reverseGeocode(fix.latitude!, fix.longitude!);
      if (mounted) {
        setState(() {
          _resolvedAddress = addr ?? '${fix.latitude!.toStringAsFixed(4)}, ${fix.longitude!.toStringAsFixed(4)}';
          _isResolvingAddress = false;
        });
      }
    } else if (mounted) {
      setState(() => _isResolvingAddress = false);
    }
  }

  Future<void> _checkInitialState() async {
    final dismissed = await AuthStorageService.isProfileBannerDismissed();
    final profile = await AuthStorageService.getUserProfile();
    if (mounted) {
      setState(() {
        _profileBannerDismissed = dismissed;
        _profileCompleted = profile?['profile_completed'] ?? false;
      });
    }
    final perm = await SosLocationService.checkPermission();
    if (perm == LocationPermission.denied && mounted) {
      LocationPermissionDialog.show(context);
    }
  }


  @override
  void dispose() {
    _notifPollTimer?.cancel();
    _scrollController.dispose();
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

  Widget _buildSosTriggerCard() {
    return Card(
      elevation: 3,
      color: Colors.red.shade700,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: () {
          Navigator.of(context).push(MaterialPageRoute(builder: (_) => const SosScreen()));
        },
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(10),
                decoration: const BoxDecoration(
                  color: Colors.white24,
                  shape: BoxShape.circle,
                ),
                child: const Icon(Icons.emergency, color: Colors.white, size: 28),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: const [
                    Text(
                      'SOS / Silent SOS / Panic',
                      style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold),
                    ),
                    SizedBox(height: 2),
                    Text(
                      'Instant response • No typing • Live GPS & profile',
                      style: TextStyle(color: Colors.white70, fontSize: 12),
                    ),
                  ],
                ),
              ),
              const Icon(Icons.arrow_forward_ios, color: Colors.white70, size: 16),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildCompleteProfileBanner() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: Colors.amber.shade50,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.amber.shade300),
      ),
      child: Row(
        children: [
          Icon(Icons.assignment_ind_outlined, color: Colors.amber.shade900, size: 22),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Complete your emergency profile',
                  style: TextStyle(color: Colors.amber.shade900, fontWeight: FontWeight.bold, fontSize: 13),
                ),
                Text(
                  'Add medical info & emergency contacts so operators receive them in an SOS.',
                  style: TextStyle(color: Colors.amber.shade900, fontSize: 11),
                ),
              ],
            ),
          ),
          TextButton(
            onPressed: () {
              Navigator.of(context).push(MaterialPageRoute(builder: (_) => const EditProfileScreen()));
            },
            child: const Text('Edit', style: TextStyle(fontWeight: FontWeight.bold)),
          ),
          IconButton(
            icon: const Icon(Icons.close, size: 16),
            onPressed: () async {
              setState(() => _profileBannerDismissed = true);
              await AuthStorageService.setProfileBannerDismissed(true);
            },
          ),
        ],
      ),
    );
  }

  String _serviceLabel(AppLocalizations l10n, String key) {
    switch (key) {
      case 'police':
        return l10n.servicePolice;
      case 'fire':
        return l10n.serviceFire;
      case 'medical':
        return l10n.serviceMedical;
      case 'disaster':
        return l10n.serviceDisaster;
      case 'women':
        return l10n.serviceWomen;
      case 'child':
        return l10n.serviceChild;
      case 'elderly':
        return l10n.serviceElderly;
      case 'railway':
        return l10n.serviceRailway;
      default:
        return key;
    }
  }

  String _serviceDescription(AppLocalizations l10n, String key) {
    switch (key) {
      case 'police':
        return l10n.helplineDescPolice;
      case 'fire':
        return l10n.helplineDescFire;
      case 'medical':
        return l10n.helplineDescMedical;
      case 'disaster':
        return l10n.helplineDescDisaster;
      case 'women':
        return l10n.helplineDescWomen;
      case 'child':
        return l10n.helplineDescChild;
      case 'elderly':
        return l10n.helplineDescElderly;
      case 'railway':
        return l10n.helplineDescRailway;
      default:
        return l10n.helplineDescEmergency;
    }
  }

  Future<void> _showIntegratedHelplineDialog() async {
    final l10n = AppLocalizations.of(context)!;
    await showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(l10n.integratedHelplineTitle),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              ...EmergencyServicesConstants.services.map((s) {
                return ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: Icon(s.icon, color: s.color),
                  title: Text('${_serviceLabel(l10n, s.key)} (${s.number})'),
                  subtitle: Text(_serviceDescription(l10n, s.key)),
                );
              }),
              ListTile(
                contentPadding: EdgeInsets.zero,
                leading: const Icon(Icons.emergency, color: Colors.red),
                title: Text(l10n.shortcutEmergencySos),
                subtitle: Text(l10n.helplineDescEmergency),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: Text(l10n.integratedHelplineClose),
          ),
        ],
      ),
    );
  }

  Future<void> _confirmDial112() async {
    final l10n = AppLocalizations.of(context)!;
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(l10n.dial112Title),
        content: Text(l10n.dial112Message),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: Text(l10n.cancelBtn),
          ),
          FilledButton.icon(
            style: FilledButton.styleFrom(backgroundColor: Colors.red),
            onPressed: () => Navigator.of(ctx).pop(true),
            icon: const Icon(Icons.call),
            label: Text(l10n.dialNowBtn),
          ),
        ],
      ),
    );
    if (ok == true) {
      final uri = Uri(scheme: 'tel', path: EmergencyServicesConstants.nationalEmergencyNumber);
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }

  Widget _buildBannerCard(AppLocalizations l10n) {
    final cs = Theme.of(context).colorScheme;
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [AppColors.primary, cs.primary.withValues(alpha: 0.82)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            l10n.bannerTagline,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 17,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 8),
          ...[
            l10n.bannerLine1,
            l10n.bannerLine2,
            l10n.bannerLine3,
            l10n.bannerLine4,
          ].map(
            (line) => Padding(
              padding: const EdgeInsets.only(bottom: 3),
              child: Row(
                children: [
                  const Icon(Icons.check_circle_outline, color: Colors.white70, size: 14),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      line,
                      style: const TextStyle(color: Colors.white, fontSize: 12.5),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildShortcutTile({
    required IconData icon,
    required String label,
    required Color color,
    required VoidCallback onTap,
    int badgeCount = 0,
  }) {
    return Semantics(
      button: true,
      label: label,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: ConstrainedBox(
          constraints: const BoxConstraints(minWidth: 48, minHeight: 48),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Stack(
                clipBehavior: Clip.none,
                children: [
                  CircleAvatar(
                    radius: 22,
                    backgroundColor: color.withValues(alpha: 0.14),
                    child: Icon(icon, color: color, size: 22),
                  ),
                  if (badgeCount > 0)
                    Positioned(
                      right: -4,
                      top: -4,
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                        decoration: BoxDecoration(
                          color: Colors.red,
                          borderRadius: BorderRadius.circular(10),
                        ),
                        child: Text(
                          badgeCount > 99 ? '99+' : '$badgeCount',
                          style: const TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold),
                        ),
                      ),
                    ),
                ],
              ),
              const SizedBox(height: 6),
              Text(
                label,
                textAlign: TextAlign.center,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w600),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildShortcutGrid(AppLocalizations l10n) {
    final shortcuts = [
      _buildShortcutTile(
        icon: Icons.person_outline,
        label: l10n.shortcutProfile,
        color: Colors.indigo,
        onTap: () async {
          final loggedIn = await AuthStorageService.isLoggedIn();
          if (!mounted) return;
          Navigator.of(context).push(
            MaterialPageRoute(
              builder: (_) => loggedIn ? const EditProfileScreen() : const LoginScreen(),
            ),
          );
        },
      ),
      _buildShortcutTile(
        icon: Icons.history,
        label: l10n.shortcutSosHistory,
        color: Colors.teal,
        onTap: () => Navigator.of(context).push(
          MaterialPageRoute(builder: (_) => const SosHistoryScreen()),
        ),
      ),
      _buildShortcutTile(
        icon: Icons.notifications_outlined,
        label: l10n.shortcutNotification,
        color: Colors.amber.shade800,
        badgeCount: _unreadNotifications,
        onTap: () async {
          await Navigator.of(context).push(
            MaterialPageRoute(builder: (_) => const NotificationsScreen()),
          );
          _refreshUnreadCount();
        },
      ),
      _buildShortcutTile(
        icon: Icons.groups_outlined,
        label: l10n.shortcutAboutUs,
        color: Colors.blueGrey,
        onTap: () => Navigator.of(context).push(
          MaterialPageRoute(builder: (_) => const AboutUsScreen()),
        ),
      ),
      _buildShortcutTile(
        icon: Icons.call,
        label: l10n.shortcutDial112,
        color: Colors.green.shade700,
        onTap: _confirmDial112,
      ),
      _buildShortcutTile(
        icon: Icons.chat_bubble_outline,
        label: l10n.shortcutChatUs,
        color: Colors.blue,
        onTap: () {
          // TODO: Implement dedicated two-way operator chat screen
          final ctx = _textBoxKey.currentContext;
          if (ctx != null) {
            Scrollable.ensureVisible(ctx, duration: const Duration(milliseconds: 350));
          }
        },
      ),
      _buildShortcutTile(
        icon: Icons.share_location,
        label: l10n.shortcutTrackMe,
        color: Colors.deepPurple,
        onTap: () => Navigator.of(context).push(
          MaterialPageRoute(builder: (_) => const TrackMeScreen()),
        ),
      ),
      _buildShortcutTile(
        icon: Icons.sos,
        label: l10n.shortcutEmergencySos,
        color: Colors.red,
        onTap: () => Navigator.of(context).push(
          MaterialPageRoute(builder: (_) => const SosScreen(serviceCategory: 'general')),
        ),
      ),
    ];

    return GridView.count(
      crossAxisCount: 4,
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      mainAxisSpacing: 8,
      crossAxisSpacing: 4,
      childAspectRatio: 0.92,
      children: shortcuts,
    );
  }

  Widget _buildServiceGrid(AppLocalizations l10n) {
    return GridView.count(
      crossAxisCount: 4,
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      mainAxisSpacing: 10,
      crossAxisSpacing: 8,
      childAspectRatio: 0.88,
      children: EmergencyServicesConstants.services.map((s) {
        final label = _serviceLabel(l10n, s.key);
        return Semantics(
          button: true,
          label: '$label ${s.number}',
          child: InkWell(
            onTap: () => ServiceSosBottomSheet.show(
              context,
              service: s,
              serviceLabel: label,
            ),
            borderRadius: BorderRadius.circular(14),
            child: Container(
              constraints: const BoxConstraints(minWidth: 48, minHeight: 48),
              padding: const EdgeInsets.all(6),
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.surface,
                borderRadius: BorderRadius.circular(14),
                border: Border.all(
                  color: s.color.withValues(alpha: 0.25),
                ),
              ),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(s.icon, color: s.color, size: 26),
                  const SizedBox(height: 5),
                  Text(
                    label,
                    textAlign: TextAlign.center,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w600),
                  ),
                  Text(
                    s.number,
                    style: TextStyle(fontSize: 10, color: s.color, fontWeight: FontWeight.bold),
                  ),
                ],
              ),
            ),
          ),
        );
      }).toList(),
    );
  }

  Widget _buildHomeLocationBar(AppLocalizations l10n) {
    return InkWell(
      onTap: _locationOff
          ? () async {
              await SosLocationService.requestPermission();
              await _refreshHomeLocationBar();
            }
          : _refreshHomeLocationBar,
      borderRadius: BorderRadius.circular(12),
      child: Container(
        constraints: const BoxConstraints(minHeight: 48),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        decoration: BoxDecoration(
          color: _locationOff
              ? Colors.amber.withValues(alpha: 0.14)
              : Theme.of(context).colorScheme.surface,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: _locationOff ? Colors.amber : AppColors.border,
          ),
        ),
        child: Row(
          children: [
            Icon(
              _locationOff ? Icons.location_off : Icons.location_on,
              color: _locationOff ? Colors.amber.shade800 : AppColors.primary,
              size: 20,
            ),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                _locationOff
                    ? l10n.locationOffTapToEnable
                    : _isResolvingAddress && _resolvedAddress == null
                        ? l10n.locationResolving
                        : (_resolvedAddress ?? l10n.locationUnavailable),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w500),
              ),
            ),
            IconButton(
              icon: _isResolvingAddress
                  ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.refresh, size: 20),
              onPressed: _refreshHomeLocationBar,
              tooltip: 'Refresh location',
            ),
          ],
        ),
      ),
    );
  }

  Widget _build112TextAndVoiceCard(AppLocalizations l10n) {
    final cs = Theme.of(context).colorScheme;
    return Container(
      key: _textBoxKey,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: cs.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: cs.outline.withValues(alpha: 0.25)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.04),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              const Icon(Icons.edit_note_rounded, color: AppColors.primary, size: 20),
              const SizedBox(width: 8),
              const Expanded(
                child: Text(
                  'Briefly describe the situation',
                  style: TextStyle(fontWeight: FontWeight.w700, fontSize: 14),
                ),
              ),
              // Compact language pill for voice/text analysis
              DropdownButtonHideUnderline(
                child: DropdownButton<EmergencyLanguageOption>(
                  value: _selectedLanguage,
                  isDense: true,
                  style: TextStyle(fontSize: 12, color: cs.primary, fontWeight: FontWeight.w600),
                  items: EmergencyLanguageOption.all
                      .map((opt) => DropdownMenuItem(
                            value: opt,
                            child: Text(opt.displayName),
                          ))
                      .toList(),
                  onChanged: _isSubmitting ? null : _onLanguageChanged,
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          TextField(
            controller: _textController,
            keyboardType: TextInputType.multiline,
            minLines: 2,
            maxLines: 4,
            decoration: InputDecoration(
              hintText: 'Type emergency details or tap the mic to speak...',
              filled: true,
              fillColor: cs.surfaceContainerHighest.withValues(alpha: 0.4),
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(12),
                borderSide: BorderSide.none,
              ),
              contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
              suffixIcon: !kIsWeb
                  ? IconButton(
                      icon: Icon(
                        _isSarvamRecording ? Icons.stop_circle : Icons.mic,
                        color: _isSarvamRecording ? Colors.red : AppColors.primary,
                        size: 26,
                      ),
                      tooltip: _isSarvamRecording ? 'Stop Voice Input' : 'Speak Emergency',
                      onPressed: _isSubmitting || _isTranscribing
                          ? null
                          : _isSarvamRecording
                              ? _stopSarvamRecording
                              : _startSarvamRecording,
                    )
                  : null,
            ),
          ),
          if (_isSarvamRecording)
            const Padding(
              padding: EdgeInsets.only(top: 6),
              child: Text(
                'Listening... Tap mic icon to stop and transcribe',
                style: TextStyle(fontSize: 12, color: Colors.red, fontWeight: FontWeight.w600),
              ),
            ),
          if (_isTranscribing)
            const Padding(
              padding: EdgeInsets.only(top: 6),
              child: Row(
                children: [
                  SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2)),
                  SizedBox(width: 8),
                  Text('Transcribing voice...', style: TextStyle(fontSize: 12)),
                ],
              ),
            ),
          const SizedBox(height: 10),
          Row(
            children: [
              if (!kIsWeb)
                Expanded(
                  child: SizedBox(
                    height: 48,
                    child: OutlinedButton.icon(
                      icon: Icon(
                        _isRecording ? Icons.stop_rounded : Icons.keyboard_voice_outlined,
                        color: _isRecording ? Colors.red : AppColors.primary,
                      ),
                      label: Text(_isRecording ? 'Stop Audio' : 'Record Voice'),
                      onPressed: _isSubmitting || _isSarvamRecording || _isTranscribing
                          ? null
                          : _isRecording
                              ? _stopRecording
                              : _startRecording,
                    ),
                  ),
                ),
              if (!kIsWeb) const SizedBox(width: 10),
              Expanded(
                child: SizedBox(
                  height: 48,
                  child: FilledButton.icon(
                    style: FilledButton.styleFrom(backgroundColor: AppColors.primary),
                    icon: _isSubmitting
                        ? const SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                          )
                        : const Icon(Icons.send_rounded),
                    label: Text(_audioPath != null ? 'Send Voice + Text' : 'Send Report'),
                    onPressed: _isSubmitting || _isTranscribing
                        ? null
                        : (_audioPath != null ? _submitAudioEmergency : _submitTextEmergency),
                  ),
                ),
              ),
            ],
          ),
          if (_audioPath != null)
            Padding(
              padding: const EdgeInsets.only(top: 6),
              child: Row(
                children: [
                  const Icon(Icons.audiotrack, size: 14, color: Colors.green),
                  const SizedBox(width: 4),
                  Expanded(
                    child: Text(
                      'Voice clip attached: ${path.basename(_audioPath!)}',
                      style: const TextStyle(fontSize: 11.5, color: Colors.green),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  InkWell(
                    onTap: () => setState(() => _audioPath = null),
                    child: const Icon(Icons.close, size: 16, color: Colors.grey),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return Scaffold(
      drawer: EmergencyDrawer(
        currentRoute: DrawerRouteItem.home,
        onProfileUpdated: _checkInitialState,
      ),
      appBar: AppBar(
        centerTitle: true,
        title: Text(l10n.appTitle, style: const TextStyle(fontWeight: FontWeight.bold)),
        elevation: 0,
        actions: [
          IconButton(
            icon: const Icon(Icons.info_outline),
            tooltip: l10n.integratedHelplineTitle,
            onPressed: _showIntegratedHelplineDialog,
          ),
        ],
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          controller: _scrollController,
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              _buildBannerCard(l10n),
              const SizedBox(height: 14),
              _buildShortcutGrid(l10n),
              const SizedBox(height: 14),
              Text(
                l10n.sectionContactEmergencyServices,
                style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 10),
              _buildServiceGrid(l10n),
              const SizedBox(height: 14),
              if (!_profileCompleted && !_profileBannerDismissed) ...[
                _buildCompleteProfileBanner(),
                const SizedBox(height: 12),
              ],
              _build112TextAndVoiceCard(l10n),
              const SizedBox(height: 12),
              _buildHomeLocationBar(l10n),
              if (_statusMessage != null) ...[
                const SizedBox(height: 12),
                Text(
                  _statusMessage!,
                  style: TextStyle(
                    color: AppColors.secondaryText,
                    fontSize: 13,
                  ),
                ),
              ],
              if (_lastSavedCall != null) ...[
                const SizedBox(height: 12),
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
