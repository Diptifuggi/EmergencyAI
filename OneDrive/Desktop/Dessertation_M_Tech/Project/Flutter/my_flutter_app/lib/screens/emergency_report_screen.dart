import 'dart:async';
import 'dart:io';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter/foundation.dart' show debugPrint, kIsWeb;
import 'package:flutter/material.dart';
import 'package:path/path.dart' as path;
import 'package:path_provider/path_provider.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:record/record.dart';
import 'package:speech_to_text/speech_to_text.dart';

import '../core/language/emergency_language_option.dart';
import '../core/language/language_mapper.dart';
import '../core/network/api_client.dart';
import '../models/emergency_call.dart';
import '../services/emergency_api_service.dart';
import '../widgets/app_colors.dart';

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
  final _speech = SpeechToText();

  EmergencyLanguageOption _selectedLanguage = EmergencyLanguageOption.english;
  List<LocaleName> _sttLocales = [];
  LocaleName? _activeSttLocale;

  bool _isRecording = false;
  bool _isListening = false;
  bool _isSubmitting = false;
  bool _speechAvailable = false;
  String? _audioPath;
  String? _statusMessage;
  String? _backendUrl;
  bool _isDiscoveringBackend = false;
  StreamSubscription<List<ConnectivityResult>>? _connectivitySub;

  @override
  void initState() {
    super.initState();
    _initSpeech();
    _initBackendConnection();
  }

  @override
  void dispose() {
    _connectivitySub?.cancel();
    _textController.dispose();
    _longitudeController.dispose();
    _latitudeController.dispose();
    _record.dispose();
    super.dispose();
  }

  Future<void> _initSpeech() async {
    if (kIsWeb) return;

    final available = await _speech.initialize(
      onError: (error) => _showMessage('Speech error: ${error.errorMsg}'),
      onStatus: (status) {
        if (status == 'done' || status == 'notListening') {
          if (mounted) {
            setState(() => _isListening = false);
          }
        }
      },
    );

    if (!mounted) return;

    final locales = await _speech.locales();
    if (!mounted) return;

    setState(() {
      _speechAvailable = available;
      _sttLocales = locales;
      _activeSttLocale = LanguageMapper.pickSttLocale(
        _sttLocales,
        _selectedLanguage,
      );
    });

    _logLanguageContext();
  }

  Future<void> _initBackendConnection() async {
    setState(() => _isDiscoveringBackend = true);
    try {
      final url = await ApiClient.getBaseUrl();
      if (!mounted) return;
      setState(() => _backendUrl = url);
    } finally {
      if (mounted) setState(() => _isDiscoveringBackend = false);
    }

    _connectivitySub = Connectivity().onConnectivityChanged.listen((results) async {
      final onWifi = results.contains(ConnectivityResult.wifi) ||
          results.contains(ConnectivityResult.ethernet);
      if (!onWifi || !mounted) return;

      setState(() => _isDiscoveringBackend = true);
      try {
        final url = await ApiClient.refreshBaseUrl();
        if (!mounted) return;
        setState(() => _backendUrl = url);
        debugPrint('[EmergencyIQ] Backend refreshed after Wi-Fi connect: $url');
      } finally {
        if (mounted) setState(() => _isDiscoveringBackend = false);
      }
    });
  }

  String _formatSavedCall(EmergencyCall call) {
    final shortId = call.id.length > 8 ? '${call.id.substring(0, 8)}…' : call.id;
    final lat = call.latitude?.toString() ?? 'not set';
    final long = call.longitude?.toString() ?? 'not set';
    return 'Saved (id: $shortId). Lat: $lat, Long: $long. Status: ${call.status}.';
  }

  void _onLanguageChanged(EmergencyLanguageOption? value) {
    if (value == null) return;
    setState(() {
      _selectedLanguage = value;
      _activeSttLocale = LanguageMapper.pickSttLocale(_sttLocales, value);
    });
    _logLanguageContext();
  }

  String? _resolveApiLanguage() {
    return LanguageMapper.resolveApiCode(selected: _selectedLanguage);
  }

  void _logLanguageContext() {
    final apiLanguage = _resolveApiLanguage();
    debugPrint('[EmergencyIQ] Selected language: ${_selectedLanguage.displayName}');
    debugPrint(
      '[EmergencyIQ] STT locale: ${_activeSttLocale?.localeId ?? 'unavailable'}',
    );
    debugPrint('[EmergencyIQ] API language: ${apiLanguage ?? 'invalid'}');
  }

  Future<void> _startListening() async {
    if (kIsWeb) {
      _showMessage('Speech recognition is not supported on Web.');
      return;
    }

    if (!_speechAvailable) {
      _showMessage('Speech recognition is not available on this device.');
      return;
    }

    final permission = await Permission.microphone.request();
    if (!permission.isGranted) {
      _showMessage('Microphone permission is required for speech recognition.');
      return;
    }

    final locale = _activeSttLocale ??
        LanguageMapper.pickSttLocale(_sttLocales, _selectedLanguage);
    if (locale == null) {
      _showMessage(
        'No speech locale found for ${_selectedLanguage.displayName}.',
      );
      return;
    }

    setState(() {
      _activeSttLocale = locale;
      _isListening = true;
      _statusMessage = 'Listening in ${_selectedLanguage.displayName}...';
    });
    _logLanguageContext();

    await _speech.listen(
      onResult: (result) {
        setState(() {
          _textController.text = result.recognizedWords;
          _statusMessage = result.finalResult
              ? 'Speech captured.'
              : 'Listening: ${result.recognizedWords}';
        });
      },
      listenOptions: SpeechListenOptions(
        localeId: locale.localeId,
        listenMode: ListenMode.confirmation,
      ),
    );
  }

  Future<void> _stopListening() async {
    await _speech.stop();
    setState(() => _isListening = false);
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

    setState(() {
      _isRecording = true;
      _audioPath = filePath;
      _statusMessage = 'Recording audio...';
    });
  }

  Future<void> _stopRecording() async {
    if (!_isRecording) return;

    final savedPath = await _record.stop();
    setState(() {
      _isRecording = false;
      _audioPath = savedPath ?? _audioPath;
      _statusMessage = _audioPath == null
          ? 'Audio recording stopped, but no file was created.'
          : 'Audio saved to ${path.basename(_audioPath!)}';
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
      final call = await EmergencyApiService().submitTextEmergency(
        text: text,
        language: language!,
        latitude: _parseCoordinate(_latitudeController.text),
        longitude: _parseCoordinate(_longitudeController.text),
      );
      _showMessage(_formatSavedCall(call));
      _textController.clear();
    } catch (error) {
      _showMessage('Failed to send emergency: $error');
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

    final transcription = _textController.text.trim();
    final language = _resolveApiLanguage();

    if (!LanguageMapper.isValidApiCode(language)) {
      _showMessage(
        'Could not determine a valid EmergencyIQ language. Please select English, Hindi, Gujarati, or Marathi.',
      );
      return;
    }

    _logLanguageContext();

    setState(() => _isSubmitting = true);
    try {
      final service = EmergencyApiService();
      if (transcription.isNotEmpty) {
        final call = await service.submitVoiceAndText(
          audioFile: file,
          transcription: transcription,
          language: language!,
          latitude: _parseCoordinate(_latitudeController.text),
          longitude: _parseCoordinate(_longitudeController.text),
          clientMetadata: {
            'platform': 'flutter',
            'recorded_at': DateTime.now().toIso8601String(),
            'selected_language': _selectedLanguage.displayName,
            'stt_locale': _activeSttLocale?.localeId,
          },
        );
        _showMessage(_formatSavedCall(call));
        _textController.clear();
      } else {
        final call = await service.submitAudioEmergency(
          audioFile: file,
          language: language!,
          latitude: _parseCoordinate(_latitudeController.text),
          longitude: _parseCoordinate(_longitudeController.text),
        );
        _showMessage(
          '${_formatSavedCall(call)} Add text next time for full voice+text storage.',
        );
      }
      setState(() {
        _audioPath = null;
      });
    } catch (error) {
      _showMessage('Failed to send voice emergency: $error');
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

  Widget _buildTextField({
    required String label,
    required TextEditingController controller,
    TextInputType keyboardType = TextInputType.text,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: const TextStyle(fontWeight: FontWeight.w600)),
        const SizedBox(height: 8),
        TextField(
          controller: controller,
          keyboardType: keyboardType,
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
            contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
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
        if (_activeSttLocale != null)
          Padding(
            padding: const EdgeInsets.only(top: 6),
            child: Text(
              'STT locale: ${_activeSttLocale!.name}',
              style: TextStyle(fontSize: 12, color: AppColors.secondaryText),
            ),
          ),
      ],
    );
  }

  Widget _buildBackendBanner() {
    final label = _isDiscoveringBackend
        ? 'Finding backend on Wi-Fi…'
        : 'Backend: ${_backendUrl ?? 'not connected'}';
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: AppColors.cardBackground,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.border),
      ),
      child: Text(
        label,
        style: TextStyle(fontSize: 12, color: AppColors.secondaryText),
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
                  icon: Icon(_isListening ? Icons.stop_circle_outlined : Icons.mic_none),
                  label: Text(_isListening ? 'Stop Listening' : 'Speak Emergency (STT)'),
                  onPressed: _isSubmitting
                      ? null
                      : _isListening
                          ? _stopListening
                          : _startListening,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: _isListening ? AppColors.dangerRed : AppColors.primary,
                    padding: const EdgeInsets.symmetric(vertical: 14),
                  ),
                ),
              ],
              const SizedBox(height: 14),
              Row(
                children: [
                  Expanded(
                    child: _buildTextField(
                      label: 'Latitude (optional)',
                      controller: _latitudeController,
                      keyboardType: TextInputType.number,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: _buildTextField(
                      label: 'Longitude (optional)',
                      controller: _longitudeController,
                      keyboardType: TextInputType.number,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 20),
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
                        icon: Icon(_isRecording ? Icons.stop_rounded : Icons.mic_rounded),
                        label: Text(_isRecording ? 'Stop Recording' : 'Start Recording'),
                        onPressed: _isSubmitting
                            ? null
                            : _isRecording
                                ? _stopRecording
                                : _startRecording,
                        style: ElevatedButton.styleFrom(
                          backgroundColor:
                              _isRecording ? AppColors.dangerRed : AppColors.primary,
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
                  onPressed: _isSubmitting ? null : _submitAudioEmergency,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppColors.secondaryText,
                    foregroundColor: AppColors.primaryText,
                    padding: const EdgeInsets.symmetric(vertical: 16),
                  ),
                ),
                const SizedBox(height: 8),
                const Text(
                  'Tip: speak or type the emergency text above, then submit so voice and text are stored together.',
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
            ],
          ),
        ),
      ),
    );
  }
}
