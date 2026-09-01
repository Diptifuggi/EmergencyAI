import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';

import '../models/emergency_location.dart';
import '../services/location_service.dart';
import '../widgets/app_colors.dart';

class MapScreen extends StatefulWidget {
  /// Optional: pass a location to display. If null, shows current GPS location.
  final EmergencyLocation? initialLocation;
  final String? title;

  const MapScreen({
    super.key,
    this.initialLocation,
    this.title,
  });

  @override
  State<MapScreen> createState() => _MapScreenState();
}

class _MapScreenState extends State<MapScreen> {
  GoogleMapController? _mapController;
  final LocationService _locationService = LocationService();

  EmergencyLocation? _currentLocation;
  String? _errorMessage;
  bool _isLoading = true;
  String _snapshotStatus = 'Waiting for map to render...';
  Uint8List? _snapshot;
  final Set<Marker> _markers = {};

  @override
  void initState() {
    super.initState();
    _initializeLocation();
  }

  @override
  void dispose() {
    _mapController?.dispose();
    super.dispose();
  }

  Future<void> _initializeLocation() async {
    try {
      final location =
          widget.initialLocation ?? await _locationService.getCurrentLocation();
      if (mounted) {
        setState(() {
          _currentLocation = location;
          _errorMessage = null;
          _isLoading = false;
          _addMarker(location);
        });
      }
    } catch (error) {
      if (mounted) {
        setState(() {
          _errorMessage = error.toString();
          _isLoading = false;
        });
      }
    }
  }

  void _addMarker(EmergencyLocation location) {
    _markers.clear();
    _markers.add(
      Marker(
        markerId: const MarkerId('caller_location'),
        position: LatLng(location.latitude, location.longitude),
        infoWindow: InfoWindow(
          title: 'Caller Location',
          snippet: 'Lat: ${location.latitude.toStringAsFixed(5)}, '
              'Lon: ${location.longitude.toStringAsFixed(5)}\n'
              'Accuracy: ±${location.accuracy.toStringAsFixed(1)}m',
        ),
      ),
    );
  }

  void _onMapCreated(GoogleMapController controller) {
    _mapController = controller;
    if (_currentLocation != null) {
      _animateToLocation(_currentLocation!);
      _captureSnapshotAfterRender();
    }
  }

  Future<void> _captureSnapshotAfterRender() async {
    if (!mounted || _mapController == null || _currentLocation == null) return;
    setState(() => _snapshotStatus = 'Rendering caller location map...');
    await Future<void>.delayed(const Duration(milliseconds: 1200));
    if (!mounted || _mapController == null || _currentLocation == null) return;
    try {
      final snapshot = await _mapController!.takeSnapshot();
      if (!mounted) return;
      if (snapshot == null || snapshot.isEmpty) {
        setState(() => _snapshotStatus = 'Unable to capture map');
        return;
      }
      setState(() {
        _snapshot = snapshot;
        _snapshotStatus = 'Map snapshot available';
      });
    } catch (error) {
      if (mounted)
        setState(() => _snapshotStatus = 'Unable to capture map: $error');
    }
  }

  void _animateToLocation(EmergencyLocation location) {
    final controller = _mapController;
    if (controller == null) return;
    controller.animateCamera(
      CameraUpdate.newCameraPosition(
        CameraPosition(
          target: LatLng(location.latitude, location.longitude),
          zoom: 17,
        ),
      ),
    );
  }

  Future<void> _refreshLocation() async {
    setState(() => _isLoading = true);
    await _initializeLocation();
  }

  Widget _buildLoadingState() {
    return const Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          CircularProgressIndicator(),
          SizedBox(height: 16),
          Text('Getting your location...'),
        ],
      ),
    );
  }

  Widget _buildErrorState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.location_off, size: 48, color: Colors.red),
          const SizedBox(height: 16),
          Text(
            'Location Error',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 8),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 24),
            child: Text(
              _errorMessage ?? 'Failed to get location',
              textAlign: TextAlign.center,
              style: TextStyle(color: AppColors.secondaryText),
            ),
          ),
          const SizedBox(height: 24),
          ElevatedButton.icon(
            onPressed: _refreshLocation,
            icon: const Icon(Icons.refresh),
            label: const Text('Try Again'),
          ),
        ],
      ),
    );
  }

  Widget _buildLocationInfo() {
    if (_currentLocation == null) return const SizedBox();

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.cardBackground,
        border: Border.all(color: AppColors.border),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Current Location',
            style: Theme.of(context).textTheme.labelLarge,
          ),
          const SizedBox(height: 8),
          Text(
            'Latitude: ${_currentLocation!.latitude.toStringAsFixed(6)}',
            style: TextStyle(fontSize: 13, color: AppColors.secondaryText),
          ),
          Text(
            'Longitude: ${_currentLocation!.longitude.toStringAsFixed(6)}',
            style: TextStyle(fontSize: 13, color: AppColors.secondaryText),
          ),
          Text(
            'Accuracy: ±${_currentLocation!.accuracy.toStringAsFixed(1)}m',
            style: TextStyle(fontSize: 13, color: AppColors.secondaryText),
          ),
          Text(
            'Captured: ${_currentLocation!.timestamp.toLocal()}',
            style: TextStyle(fontSize: 12, color: AppColors.secondaryText),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return PopScope<Uint8List>(
      canPop: false,
      onPopInvokedWithResult: (didPop, result) {
        if (!didPop) Navigator.of(context).pop<Uint8List>(_snapshot);
      },
      child: Scaffold(
        appBar: AppBar(
          title: Text(widget.title ?? 'Caller Location Map'),
          backgroundColor: AppColors.background,
          foregroundColor: AppColors.primaryText,
          elevation: 0,
          leading: IconButton(
            icon: const Icon(Icons.arrow_back),
            onPressed: () => Navigator.of(context).pop<Uint8List>(_snapshot),
            tooltip: 'Return to emergency report',
          ),
          actions: [
            if (_currentLocation != null)
              IconButton(
                icon: const Icon(Icons.my_location),
                onPressed: () => _animateToLocation(_currentLocation!),
                tooltip: 'Center on location',
              ),
            if (_currentLocation != null)
              IconButton(
                icon: const Icon(Icons.refresh),
                onPressed: _refreshLocation,
                tooltip: 'Refresh location',
              ),
          ],
        ),
        backgroundColor: AppColors.background,
        body: Stack(
          children: [
            if (_isLoading)
              _buildLoadingState()
            else if (_errorMessage != null)
              _buildErrorState()
            else if (_currentLocation != null)
              Column(
                children: [
                  Expanded(
                    child: GoogleMap(
                      onMapCreated: _onMapCreated,
                      initialCameraPosition: CameraPosition(
                        target: LatLng(
                          _currentLocation!.latitude,
                          _currentLocation!.longitude,
                        ),
                        zoom: 17,
                      ),
                      markers: _markers,
                      myLocationEnabled: true,
                      myLocationButtonEnabled: false,
                      compassEnabled: true,
                      scrollGesturesEnabled: true,
                      zoomGesturesEnabled: true,
                      tiltGesturesEnabled: false,
                      rotateGesturesEnabled: false,
                      mapType: MapType.normal,
                    ),
                  ),
                  Padding(
                    padding: const EdgeInsets.all(12),
                    child: Column(
                      children: [
                        _buildLocationInfo(),
                        const SizedBox(height: 6),
                        Text(_snapshotStatus),
                      ],
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
