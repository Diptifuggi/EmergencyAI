class EmergencyLocation {
  final double latitude;
  final double longitude;
  final double accuracy;
  final DateTime timestamp;

  const EmergencyLocation({
    required this.latitude,
    required this.longitude,
    required this.accuracy,
    required this.timestamp,
  });
}