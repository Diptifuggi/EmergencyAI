import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import '../services/sos_location_service.dart';

class LocationPermissionDialog extends StatelessWidget {
  const LocationPermissionDialog({super.key});

  static Future<bool> show(BuildContext context) async {
    final result = await showDialog<bool>(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => const LocationPermissionDialog(),
    );
    return result ?? false;
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      title: Row(
        children: const [
          Icon(Icons.location_on, color: Colors.redAccent, size: 28),
          SizedBox(width: 8),
          Text('Location Permission', style: TextStyle(fontWeight: FontWeight.bold)),
        ],
      ),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: const [
          Text(
            'EmergencyIQ uses your precise location to route emergency responders and medical assistance to your exact spot.',
            style: TextStyle(fontSize: 14, height: 1.4),
          ),
          SizedBox(height: 12),
          Text(
            '• Immediate dispatch during SOS\n• Live tracking for active emergencies\n• Battery-aware coordinate updates',
            style: TextStyle(fontSize: 13, color: Colors.grey, height: 1.4),
          ),
        ],
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(false),
          child: const Text('Not Now', style: TextStyle(color: Colors.grey)),
        ),
        ElevatedButton(
          style: ElevatedButton.styleFrom(
            backgroundColor: Colors.redAccent,
            foregroundColor: Colors.white,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
          ),
          onPressed: () async {
            final permission = await SosLocationService.requestPermission();
            if (context.mounted) {
              if (permission == LocationPermission.deniedForever) {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: const Text('Location is permanently disabled. Please allow it in device settings.'),
                    action: SnackBarAction(
                      label: 'Settings',
                      onPressed: () => SosLocationService.openSettings(),
                    ),
                  ),
                );
              }
              Navigator.of(context).pop(
                permission == LocationPermission.always || permission == LocationPermission.whileInUse,
              );
            }
          },
          child: const Text('Allow Location'),
        ),
      ],
    );
  }
}
