import 'package:flutter/material.dart';
import 'dart:typed_data';

import '../models/emergency_call.dart';
import 'app_colors.dart';

class EmergencyLocationCard extends StatelessWidget {
  final EmergencyCall call;
  final Uint8List? mapSnapshot;

  const EmergencyLocationCard(
      {super.key, required this.call, this.mapSnapshot});

  @override
  Widget build(BuildContext context) {
    final latitude = call.latitude;
    final longitude = call.longitude;
    if (latitude == null || longitude == null) return const SizedBox.shrink();

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
            Text('Location status: ${call.locationStatus}'),
            const SizedBox(height: 8),
            SizedBox(
              height: 220,
              child: ClipRRect(
                borderRadius: BorderRadius.circular(10),
                child: mapSnapshot != null && mapSnapshot!.isNotEmpty
                    ? Image.memory(mapSnapshot!, fit: BoxFit.cover)
                    : Container(
                        color: Colors.grey.shade200,
                        alignment: Alignment.center,
                        child: Text(
                          call.mapSnapshotAvailable
                              ? 'Map snapshot available on the server'
                              : 'Map snapshot unavailable',
                          textAlign: TextAlign.center,
                        ),
                      ),
              ),
            ),
            const SizedBox(height: 8),
            Text('Latitude: $latitude\nLongitude: $longitude'),
            if (call.locationAccuracy != null)
              Text(
                  'GPS accuracy: ${call.locationAccuracy!.toStringAsFixed(1)} m'),
            if (call.locationAddress != null &&
                call.locationAddress!.isNotEmpty)
              Text('Address: ${call.locationAddress}'),
            Text(
                'Map snapshot: ${call.mapSnapshotAvailable ? 'available' : 'unavailable'}'),
          ],
        ),
      ),
    );
  }
}
