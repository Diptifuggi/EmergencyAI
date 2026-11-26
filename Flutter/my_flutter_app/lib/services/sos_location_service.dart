import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:geolocator/geolocator.dart';
import 'package:permission_handler/permission_handler.dart';

class SosLocationFix {
  final double? latitude;
  final double? longitude;
  final double? accuracyM;
  final String locationStatus; // 'available', 'last_known', 'denied', 'unavailable'
  final DateTime recordedAt;

  SosLocationFix({
    this.latitude,
    this.longitude,
    this.accuracyM,
    required this.locationStatus,
    required this.recordedAt,
  });
}

class SosLocationService {
  /// Checks location permission status without prompting.
  static Future<LocationPermission> checkPermission() async {
    try {
      return await Geolocator.checkPermission();
    } catch (e) {
      debugPrint('[SosLocationService] Error checking permission: $e');
      return LocationPermission.denied;
    }
  }

  /// Requests location permission.
  static Future<LocationPermission> requestPermission() async {
    try {
      return await Geolocator.requestPermission();
    } catch (e) {
      debugPrint('[SosLocationService] Error requesting permission: $e');
      return LocationPermission.denied;
    }
  }

  /// Open device app settings if permission is permanently denied.
  static Future<void> openSettings() async {
    await openAppSettings();
  }

  /// Open device location service settings if GPS is switched off.
  static Future<void> openLocationSettings() async {
    await Geolocator.openLocationSettings();
  }

  /// Location capture strategy:
  /// 1. Try last known position (instant fallback).
  /// 2. If permission granted & services enabled, try fresh high-accuracy fix with 6s timeout.
  /// 3. Never throw: return graceful SosLocationFix.
  static Future<SosLocationFix> captureLocation({bool promptIfDenied = false}) async {
    final now = DateTime.now().toUtc();
    try {
      final isServiceEnabled = await Geolocator.isLocationServiceEnabled();
      if (!isServiceEnabled) {
        return SosLocationFix(
          locationStatus: 'unavailable',
          recordedAt: now,
        );
      }

      var permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied && promptIfDenied) {
        permission = await Geolocator.requestPermission();
      }

      if (permission == LocationPermission.denied ||
          permission == LocationPermission.deniedForever) {
        return SosLocationFix(
          locationStatus: 'denied',
          recordedAt: now,
        );
      }

      // Check last known location first (instant)
      Position? bestPosition;
      try {
        bestPosition = await Geolocator.getLastKnownPosition();
      } catch (_) {}

      // Attempt fresh high-accuracy position with 6-second timeout
      try {
        final freshPosition = await Geolocator.getCurrentPosition(
          desiredAccuracy: LocationAccuracy.high,
          timeLimit: const Duration(seconds: 6),
        );
        bestPosition = freshPosition;
        return SosLocationFix(
          latitude: freshPosition.latitude,
          longitude: freshPosition.longitude,
          accuracyM: freshPosition.accuracy,
          locationStatus: 'available',
          recordedAt: DateTime.now().toUtc(),
        );
      } on TimeoutException {
        // Fall back to last known position if fresh fix timed out
        if (bestPosition != null) {
          return SosLocationFix(
            latitude: bestPosition.latitude,
            longitude: bestPosition.longitude,
            accuracyM: bestPosition.accuracy,
            locationStatus: 'last_known',
            recordedAt: bestPosition.timestamp.toUtc(),
          );
        }
        return SosLocationFix(
          locationStatus: 'unavailable',
          recordedAt: now,
        );
      } catch (_) {
        if (bestPosition != null) {
          return SosLocationFix(
            latitude: bestPosition.latitude,
            longitude: bestPosition.longitude,
            accuracyM: bestPosition.accuracy,
            locationStatus: 'last_known',
            recordedAt: bestPosition.timestamp.toUtc(),
          );
        }
        return SosLocationFix(
          locationStatus: 'unavailable',
          recordedAt: now,
        );
      }
    } catch (e) {
      debugPrint('[SosLocationService] Capture failed: $e');
      return SosLocationFix(
        locationStatus: 'unavailable',
        recordedAt: now,
      );
    }
  }
}
