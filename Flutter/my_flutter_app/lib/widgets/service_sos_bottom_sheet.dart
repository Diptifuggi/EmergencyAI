import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:url_launcher/url_launcher.dart';

import '../core/constants/emergency_services.dart';
import '../l10n/app_localizations.dart';
import '../services/settings_service.dart';
import '../services/sos_location_service.dart';
import '../services/sos_queue_service.dart';

class ServiceSosBottomSheet extends StatefulWidget {
  final EmergencyServiceItem service;
  final String serviceLabel;

  const ServiceSosBottomSheet({
    super.key,
    required this.service,
    required this.serviceLabel,
  });

  static Future<void> show(
    BuildContext context, {
    required EmergencyServiceItem service,
    required String serviceLabel,
  }) {
    return showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (_) => ServiceSosBottomSheet(
        service: service,
        serviceLabel: serviceLabel,
      ),
    );
  }

  @override
  State<ServiceSosBottomSheet> createState() => _ServiceSosBottomSheetState();
}

class _ServiceSosBottomSheetState extends State<ServiceSosBottomSheet> {
  final SosQueueService _queueService = SosQueueService();
  double _holdProgress = 0.0;
  Timer? _holdTimer;

  bool _inCancelCountdown = false;
  int _countdownSeconds = 5;
  int _configuredCountdown = 5;
  bool _vibrationEnabled = true;
  Timer? _countdownTimer;

  QueuedSosAlert? _sentAlert;
  StreamSubscription<QueuedSosAlert>? _subscription;

  @override
  void initState() {
    super.initState();
    _loadSettings();
    _subscription = _queueService.statusStream.listen((alert) {
      if (mounted && _sentAlert != null && alert.id == _sentAlert!.id) {
        setState(() => _sentAlert = alert);
      }
    });
  }

  Future<void> _loadSettings() async {
    final s = await SettingsService.load();
    if (mounted) {
      setState(() {
        _configuredCountdown = s.cancelCountdownSeconds;
        _countdownSeconds = s.cancelCountdownSeconds;
        _vibrationEnabled = s.vibrationEnabled;
      });
    }
  }

  @override
  void dispose() {
    _holdTimer?.cancel();
    _countdownTimer?.cancel();
    _subscription?.cancel();
    super.dispose();
  }

  void _startHold() {
    if (_inCancelCountdown || _sentAlert != null) return;
    _holdProgress = 0.0;
    const tick = Duration(milliseconds: 50);
    const totalTicks = 2000 ~/ 50; // 2 seconds
    var count = 0;

    if (_vibrationEnabled) HapticFeedback.mediumImpact();
    _holdTimer?.cancel();
    _holdTimer = Timer.periodic(tick, (timer) {
      count++;
      setState(() => _holdProgress = count / totalTicks);
      if (count >= totalTicks) {
        timer.cancel();
        _holdProgress = 0.0;
        _startCountdown();
      }
    });
  }

  void _cancelHold() {
    _holdTimer?.cancel();
    if (_holdProgress > 0) {
      setState(() => _holdProgress = 0.0);
    }
  }

  void _startCountdown() {
    setState(() {
      _inCancelCountdown = true;
      _countdownSeconds = _configuredCountdown;
    });
    if (_vibrationEnabled) HapticFeedback.heavyImpact();

    _countdownTimer?.cancel();
    _countdownTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (_countdownSeconds <= 1) {
        timer.cancel();
        setState(() => _inCancelCountdown = false);
        _dispatchSos();
      } else {
        if (_vibrationEnabled) HapticFeedback.selectionClick();
        setState(() => _countdownSeconds--);
      }
    });
  }

  void _abortCountdown() {
    _countdownTimer?.cancel();
    setState(() => _inCancelCountdown = false);
  }

  Future<void> _dispatchSos() async {
    final fix = await SosLocationService.captureLocation(promptIfDenied: true);
    final alert = await _queueService.enqueueSos(
      alertType: 'sos',
      serviceCategory: widget.service.key,
      categorySource: 'user_selected',
      locationFix: fix,
    );
    if (mounted) {
      setState(() => _sentAlert = alert);
    }
  }

  Future<void> _openDialer() async {
    final uri = Uri(scheme: 'tel', path: widget.service.number);
    await launchUrl(uri, mode: LaunchMode.externalApplication);
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final alert = _sentAlert;
    final isConfirmed = alert != null &&
        (alert.deliveryState == SosDeliveryState.serverReceived ||
            alert.deliveryState == SosDeliveryState.acknowledgedByOperator ||
            alert.deliveryState == SosDeliveryState.verified);

    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(20, 20, 20, 24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                CircleAvatar(
                  backgroundColor: widget.service.color.withValues(alpha: 0.15),
                  child: Icon(widget.service.icon, color: widget.service.color),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    l10n.sendServiceSosTitle(widget.serviceLabel),
                    style: Theme.of(context).textTheme.titleLarge?.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            if (alert != null) ...[
              Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: isConfirmed
                      ? Colors.green.withValues(alpha: 0.12)
                      : Colors.orange.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: isConfirmed ? Colors.green : Colors.orange,
                  ),
                ),
                child: Row(
                  children: [
                    Icon(
                      isConfirmed ? Icons.check_circle : Icons.schedule_send,
                      color: isConfirmed ? Colors.green : Colors.orange,
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        isConfirmed ? l10n.sosSentConfirmed : l10n.sosQueuedOffline,
                        style: const TextStyle(fontWeight: FontWeight.w600),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
            ] else if (_inCancelCountdown) ...[
              SizedBox(
                height: 54,
                child: FilledButton.icon(
                  style: FilledButton.styleFrom(backgroundColor: Colors.red),
                  onPressed: _abortCountdown,
                  icon: const Icon(Icons.close),
                  label: Text(l10n.sendingInSeconds(_countdownSeconds)),
                ),
              ),
              const SizedBox(height: 12),
            ] else ...[
              Semantics(
                button: true,
                label: l10n.holdToSendSos,
                child: GestureDetector(
                  onLongPressStart: (_) => _startHold(),
                  onLongPressEnd: (_) => _cancelHold(),
                  onLongPressCancel: _cancelHold,
                  child: Container(
                    height: 56,
                    decoration: BoxDecoration(
                      color: widget.service.color,
                      borderRadius: BorderRadius.circular(14),
                    ),
                    child: Stack(
                      alignment: Alignment.center,
                      children: [
                        if (_holdProgress > 0)
                          Positioned.fill(
                            child: ClipRRect(
                              borderRadius: BorderRadius.circular(14),
                              child: LinearProgressIndicator(
                                value: _holdProgress,
                                backgroundColor: Colors.transparent,
                                valueColor: AlwaysStoppedAnimation<Color>(
                                  Colors.white.withValues(alpha: 0.35),
                                ),
                              ),
                            ),
                          ),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            const Icon(Icons.sos, color: Colors.white),
                            const SizedBox(width: 8),
                            Text(
                              l10n.holdToSendSos,
                              style: const TextStyle(
                                color: Colors.white,
                                fontWeight: FontWeight.bold,
                                fontSize: 16,
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 12),
            ],
            Row(
              children: [
                Expanded(
                  child: SizedBox(
                    height: 48,
                    child: OutlinedButton.icon(
                      onPressed: _openDialer,
                      icon: const Icon(Icons.call),
                      label: Text(l10n.callNumberBtn(widget.service.number)),
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: SizedBox(
                    height: 48,
                    child: TextButton(
                      onPressed: () => Navigator.of(context).pop(),
                      child: Text(l10n.cancelBtn),
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
