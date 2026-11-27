import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../services/settings_service.dart';
import '../services/sos_location_service.dart';
import '../services/sos_queue_service.dart';

class SosScreen extends StatefulWidget {
  final String serviceCategory;
  final String categorySource;

  const SosScreen({
    super.key,
    this.serviceCategory = 'general',
    this.categorySource = 'user_selected',
  });

  @override
  State<SosScreen> createState() => _SosScreenState();
}

class _SosScreenState extends State<SosScreen> with SingleTickerProviderStateMixin {
  final SosQueueService _queueService = SosQueueService();

  // Active state
  QueuedSosAlert? _activeAlert;
  StreamSubscription<QueuedSosAlert>? _subscription;

  // Press-and-hold progress state
  String? _holdingTrigger; // 'sos', 'panic_button'
  double _holdProgress = 0.0;
  Timer? _holdTimer;

  // Cancel countdown state (configurable from Settings, default 5 seconds)
  bool _inCancelCountdown = false;
  int _cancelCountdownSeconds = 5;
  int _configuredCountdown = 5;
  bool _vibrationEnabled = true;
  Timer? _cancelCountdownTimer;
  String? _pendingTriggerType;

  // Silent SOS discrete confirmation mode
  bool _isSilentSosActive = false;
  bool _showSilentCancel = true;

  @override
  void initState() {
    super.initState();
    _activeAlert = _queueService.currentActiveAlert;
    _loadSettings();
    _subscription = _queueService.statusStream.listen((alert) {
      if (mounted) {
        setState(() => _activeAlert = alert);
      }
    });
  }

  Future<void> _loadSettings() async {
    final s = await SettingsService.load();
    if (!mounted) return;
    setState(() {
      _configuredCountdown = s.cancelCountdownSeconds;
      _cancelCountdownSeconds = s.cancelCountdownSeconds;
      _vibrationEnabled = s.vibrationEnabled;
    });
    if (s.silentModeDefault && _activeAlert == null && mounted) {
      _triggerSilentSos();
    }
  }

  @override
  void dispose() {
    _holdTimer?.cancel();
    _cancelCountdownTimer?.cancel();
    _subscription?.cancel();
    super.dispose();
  }

  void _startHolding(String trigger, Duration holdDuration) {
    if (_inCancelCountdown) return;
    _holdingTrigger = trigger;
    _holdProgress = 0.0;

    const tickInterval = Duration(milliseconds: 50);
    final totalTicks = holdDuration.inMilliseconds / tickInterval.inMilliseconds;
    var currentTick = 0;

    HapticFeedback.mediumImpact();

    _holdTimer?.cancel();
    _holdTimer = Timer.periodic(tickInterval, (timer) {
      currentTick++;
      setState(() {
        _holdProgress = currentTick / totalTicks;
      });

      if (currentTick >= totalTicks) {
        timer.cancel();
        _onHoldCompleted(trigger);
      }
    });
  }

  void _cancelHolding() {
    _holdTimer?.cancel();
    if (_holdingTrigger != null) {
      setState(() {
        _holdingTrigger = null;
        _holdProgress = 0.0;
      });
    }
  }

  void _onHoldCompleted(String trigger) {
    _holdingTrigger = null;
    _holdProgress = 0.0;

    if (trigger == 'silent_sos') {
      _triggerSilentSos();
    } else {
      _startCancelCountdown(trigger);
    }
  }

  void _startCancelCountdown(String trigger) {
    setState(() {
      _inCancelCountdown = true;
      _cancelCountdownSeconds = _configuredCountdown;
      _pendingTriggerType = trigger;
    });

    // Sound / vibration feedback for standard SOS / Panic
    if (_vibrationEnabled) HapticFeedback.heavyImpact();

    _cancelCountdownTimer?.cancel();
    _cancelCountdownTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (_cancelCountdownSeconds <= 1) {
        timer.cancel();
        setState(() => _inCancelCountdown = false);
        _dispatchSos(_pendingTriggerType ?? 'sos');
      } else {
        if (_vibrationEnabled) HapticFeedback.selectionClick();
        setState(() {
          _cancelCountdownSeconds--;
        });
      }
    });
  }

  void _abortCountdown() {
    _cancelCountdownTimer?.cancel();
    setState(() {
      _inCancelCountdown = false;
      _pendingTriggerType = null;
    });
  }

  Future<void> _triggerSilentSos() async {
    // Silent SOS: No sound, no flash, light haptic only
    HapticFeedback.lightImpact();

    setState(() {
      _isSilentSosActive = true;
      _showSilentCancel = true;
    });

    // Capture location in parallel without blocking
    final locationFix = await SosLocationService.captureLocation(promptIfDenied: false);
    await _queueService.enqueueSos(
      alertType: 'silent_sos',
      serviceCategory: widget.serviceCategory,
      categorySource: widget.categorySource,
      locationFix: locationFix,
    );

    // Hide silent cancel button after 5 seconds to remain discreet
    Timer(const Duration(seconds: 5), () {
      if (mounted) setState(() => _showSilentCancel = false);
    });
  }

  Future<void> _dispatchSos(String trigger) async {
    // Capture location order: last known position first (instant), then high accuracy
    final locationFix = await SosLocationService.captureLocation(promptIfDenied: true);

    await _queueService.enqueueSos(
      alertType: trigger,
      serviceCategory: widget.serviceCategory,
      categorySource: widget.categorySource,
      locationFix: locationFix,
    );
  }

  Future<void> _cancelActiveSos() async {
    final success = await _queueService.cancelActiveAlert(reason: 'Cancelled by user');
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(success ? 'SOS cancelled' : 'Failed to cancel SOS')),
      );
      if (_isSilentSosActive) {
        setState(() => _isSilentSosActive = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isSilentSosActive) {
      return _buildSilentSosScreen();
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('Emergency Triggers', style: TextStyle(fontWeight: FontWeight.bold)),
        backgroundColor: Colors.grey.shade900,
        foregroundColor: Colors.white,
      ),
      backgroundColor: Colors.grey.shade900,
      body: SafeArea(
        child: _inCancelCountdown ? _buildCancelCountdownUI() : _buildTriggerButtonsUI(),
      ),
    );
  }

  Widget _buildCancelCountdownUI() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Text(
              'DISPATCHING SOS IN',
              style: TextStyle(color: Colors.redAccent, fontSize: 18, fontWeight: FontWeight.bold, letterSpacing: 1.5),
            ),
            const SizedBox(height: 24),
            Container(
              width: 140,
              height: 140,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                border: Border.all(color: Colors.redAccent, width: 4),
              ),
              child: Center(
                child: Text(
                  '$_cancelCountdownSeconds',
                  style: const TextStyle(color: Colors.white, fontSize: 64, fontWeight: FontWeight.bold),
                ),
              ),
            ),
            const SizedBox(height: 32),
            const Text(
              'Location will be attached automatically.\nPress Cancel if triggered by mistake.',
              textAlign: TextAlign.center,
              style: TextStyle(color: Colors.grey, fontSize: 14),
            ),
            const SizedBox(height: 36),
            ElevatedButton.icon(
              icon: const Icon(Icons.cancel, size: 28),
              label: const Text('CANCEL SOS', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.white,
                foregroundColor: Colors.red.shade900,
                padding: const EdgeInsets.symmetric(horizontal: 40, vertical: 18),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(30)),
              ),
              onPressed: _abortCountdown,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTriggerButtonsUI() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Live Alert Status Card
          if (_activeAlert != null) _buildAlertStatusCard(_activeAlert!),

          const SizedBox(height: 16),

          // 1. SOS Button (Hold 2s)
          _buildHoldButton(
            title: 'SOS EMERGENCY',
            subtitle: 'Hold for 2s • 5s cancel countdown • Sirens & Dispatch',
            color: Colors.red.shade700,
            icon: Icons.emergency,
            triggerName: 'sos',
            holdDuration: const Duration(seconds: 2),
            height: 150,
          ),

          const SizedBox(height: 20),

          // 2. Silent SOS (Immediate Discreet Trigger)
          Card(
            color: Colors.deepPurple.shade900.withOpacity(0.5),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(16),
              side: BorderSide(color: Colors.deepPurple.shade700),
            ),
            child: InkWell(
              borderRadius: BorderRadius.circular(16),
              onTap: _triggerSilentSos,
              child: Padding(
                padding: const EdgeInsets.all(20),
                child: Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: Colors.deepPurple.shade800,
                        shape: BoxShape.circle,
                      ),
                      child: const Icon(Icons.volume_off, color: Colors.purpleAccent, size: 28),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: const [
                          Text(
                            'SILENT SOS',
                            style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
                          ),
                          SizedBox(height: 4),
                          Text(
                            'No sound, no flash • Light haptic only • Instant discreet alert',
                            style: TextStyle(color: Colors.purpleAccent, fontSize: 12),
                          ),
                        ],
                      ),
                    ),
                    const Icon(Icons.chevron_right, color: Colors.purpleAccent),
                  ],
                ),
              ),
            ),
          ),

          const SizedBox(height: 20),

          // 3. Panic Button (Hold 3s)
          _buildHoldButton(
            title: 'PANIC BUTTON',
            subtitle: 'Hold for 3s • Dedicated rapid response',
            color: Colors.orange.shade900,
            icon: Icons.touch_app,
            triggerName: 'panic_button',
            holdDuration: const Duration(seconds: 3),
            height: 130,
          ),

          const SizedBox(height: 24),
          const Center(
            child: Text(
              'No typing required during an emergency.\nYour coordinates & encrypted profile are transmitted automatically.',
              textAlign: TextAlign.center,
              style: TextStyle(color: Colors.grey, fontSize: 12, height: 1.4),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildHoldButton({
    required String title,
    required String subtitle,
    required Color color,
    required IconData icon,
    required String triggerName,
    required Duration holdDuration,
    required double height,
  }) {
    final isHolding = _holdingTrigger == triggerName;

    return GestureDetector(
      onTapDown: (_) => _startHolding(triggerName, holdDuration),
      onTapUp: (_) => _cancelHolding(),
      onTapCancel: _cancelHolding,
      child: Container(
        height: height,
        decoration: BoxDecoration(
          color: color,
          borderRadius: BorderRadius.circular(20),
          boxShadow: [
            BoxShadow(
              color: color.withOpacity(0.4),
              blurRadius: 12,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Stack(
          children: [
            // Progress fill on hold
            if (isHolding)
              Positioned.fill(
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(20),
                  child: LinearProgressIndicator(
                    value: _holdProgress,
                    backgroundColor: Colors.transparent,
                    valueColor: AlwaysStoppedAnimation<Color>(Colors.white.withOpacity(0.3)),
                  ),
                ),
              ),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
              child: Row(
                children: [
                  Icon(icon, size: 48, color: Colors.white),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          title,
                          style: const TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.bold),
                        ),
                        const SizedBox(height: 6),
                        Text(
                          isHolding ? 'Keep holding...' : subtitle,
                          style: TextStyle(
                            color: Colors.white.withOpacity(0.85),
                            fontSize: 13,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildAlertStatusCard(QueuedSosAlert alert) {
    Color statusColor;
    String statusText;
    IconData statusIcon;

    switch (alert.deliveryState) {
      case SosDeliveryState.queued:
        statusColor = Colors.amber;
        statusText = 'Queued locally (retrying...)';
        statusIcon = Icons.cloud_queue;
        break;
      case SosDeliveryState.sending:
        statusColor = Colors.blue;
        statusText = 'Sending to EmergencyIQ...';
        statusIcon = Icons.cloud_upload;
        break;
      case SosDeliveryState.serverReceived:
        statusColor = Colors.teal;
        statusText = 'Server Received • Awaiting Operator';
        statusIcon = Icons.check_circle_outline;
        break;
      case SosDeliveryState.acknowledgedByOperator:
        statusColor = Colors.green;
        statusText = 'Acknowledged by Operator';
        statusIcon = Icons.verified_user;
        break;
      case SosDeliveryState.verified:
        statusColor = Colors.greenAccent;
        statusText = 'Verified & Dispatched';
        statusIcon = Icons.local_police;
        break;
      case SosDeliveryState.cancelled:
        statusColor = Colors.grey;
        statusText = 'Cancelled';
        statusIcon = Icons.cancel;
        break;
      case SosDeliveryState.closed:
        statusColor = Colors.blueGrey;
        statusText = 'Resolved & Closed';
        statusIcon = Icons.done_all;
        break;
      case SosDeliveryState.failed:
        statusColor = Colors.red;
        statusText = 'Failed to transmit';
        statusIcon = Icons.error_outline;
        break;
    }

    return Card(
      color: Colors.grey.shade900,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(color: statusColor.withOpacity(0.6), width: 1.5),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(statusIcon, color: statusColor, size: 22),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    statusText,
                    style: TextStyle(color: statusColor, fontWeight: FontWeight.bold, fontSize: 14),
                  ),
                ),
                if (alert.deliveryState != SosDeliveryState.closed &&
                    alert.deliveryState != SosDeliveryState.cancelled)
                  TextButton(
                    onPressed: _cancelActiveSos,
                    style: TextButton.styleFrom(foregroundColor: Colors.redAccent),
                    child: const Text('Cancel SOS'),
                  ),
              ],
            ),
            const Divider(color: Colors.grey, height: 16),
            Text(
              'Alert Type: ${alert.alertType.toUpperCase()} | Location: ${alert.locationStatus}',
              style: const TextStyle(color: Colors.white70, fontSize: 12),
            ),
            if (alert.latitude != null && alert.longitude != null)
              Text(
                'Live GPS: ±${alert.accuracyM?.toStringAsFixed(1) ?? 'N/A'}m accuracy',
                style: const TextStyle(color: Colors.greenAccent, fontSize: 12),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildSilentSosScreen() {
    // Neutral, discreet screen with dark background
    return Scaffold(
      backgroundColor: Colors.black,
      body: SafeArea(
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Icon(Icons.check_circle_outline, color: Colors.white24, size: 48),
                const SizedBox(height: 16),
                const Text(
                  'Emergency Request Registered',
                  style: TextStyle(color: Colors.white38, fontSize: 14),
                ),
                const SizedBox(height: 40),
                if (_showSilentCancel)
                  TextButton(
                    onPressed: _cancelActiveSos,
                    child: const Text(
                      'Cancel (5s)',
                      style: TextStyle(color: Colors.white30, fontSize: 12),
                    ),
                  ),
                const SizedBox(height: 20),
                TextButton(
                  onPressed: () => setState(() => _isSilentSosActive = false),
                  child: const Text(
                    'Return to App',
                    style: TextStyle(color: Colors.white54, fontSize: 13),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
