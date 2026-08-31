import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';

import '../models/emergency_call.dart';
import 'app_colors.dart';

const _mapTileUrl = String.fromEnvironment(
  'MAP_TILE_URL',
  defaultValue: 'http://10.0.2.2:8081/tiles/{z}/{x}/{y}.png',
);

class EmergencyLocationCard extends StatelessWidget {
  final EmergencyCall call;

  const EmergencyLocationCard({super.key, required this.call});

  @override
  Widget build(BuildContext context) {
    final latitude = call.latitude;
    final longitude = call.longitude;
    if (latitude == null || longitude == null) return const SizedBox.shrink();

    final point = LatLng(latitude, longitude);
    return Card(
      color: AppColors.cardBackground,
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text('Emergency location', style: TextStyle(fontWeight: FontWeight.w700)),
            const SizedBox(height: 8),
            SizedBox(
              height: 220,
              child: ClipRRect(
                borderRadius: BorderRadius.circular(10),
                child: FlutterMap(
                  options: MapOptions(initialCenter: point, initialZoom: 15),
                  children: [
                    TileLayer(
                      urlTemplate: _mapTileUrl,
                      userAgentPackageName: 'com.emergencyiq.app',
                    ),
                    MarkerLayer(
                      markers: [
                        Marker(
                          point: point,
                          width: 48,
                          height: 48,
                          child: const Icon(Icons.location_pin, color: Colors.red, size: 44),
                        ),
                      ],
                    ),
                    const RichAttributionWidget(
                      attributions: [TextSourceAttribution('© OpenStreetMap contributors')],
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 8),
            Text('Latitude: $latitude\nLongitude: $longitude'),
            if (call.locationAccuracy != null)
              Text('GPS accuracy: ${call.locationAccuracy!.toStringAsFixed(1)} m'),
            if (call.locationAddress != null && call.locationAddress!.isNotEmpty)
              Text('Address: ${call.locationAddress}'),
          ],
        ),
      ),
    );
  }
}