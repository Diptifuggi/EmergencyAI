import 'package:flutter/material.dart';

class EmergencyServiceItem {
  final String key; // Matches backend service_category enum
  final String number;
  final IconData icon;
  final Color color;

  const EmergencyServiceItem({
    required this.key,
    required this.number,
    required this.icon,
    required this.color,
  });
}

class EmergencyServicesConstants {
  static const String nationalEmergencyNumber = '112';

  static const List<EmergencyServiceItem> services = [
    EmergencyServiceItem(
      key: 'police',
      number: '100',
      icon: Icons.local_police_outlined,
      color: Color(0xFF1E40AF),
    ),
    EmergencyServiceItem(
      key: 'fire',
      number: '101',
      icon: Icons.local_fire_department_outlined,
      color: Color(0xFFDC2626),
    ),
    EmergencyServiceItem(
      key: 'medical',
      number: '108',
      icon: Icons.medical_services_outlined,
      color: Color(0xFF059669),
    ),
    EmergencyServiceItem(
      key: 'disaster',
      number: '1070',
      icon: Icons.flood_outlined,
      color: Color(0xFFD97706),
    ),
    EmergencyServiceItem(
      key: 'women',
      number: '181',
      icon: Icons.woman_outlined,
      color: Color(0xFF9333EA),
    ),
    EmergencyServiceItem(
      key: 'child',
      number: '1098',
      icon: Icons.child_care_outlined,
      color: Color(0xFF0284C7),
    ),
    EmergencyServiceItem(
      key: 'elderly',
      number: '14567',
      icon: Icons.elderly_outlined,
      color: Color(0xFF4F46E5),
    ),
    EmergencyServiceItem(
      key: 'railway',
      number: '139',
      icon: Icons.train_outlined,
      color: Color(0xFF0F766E),
    ),
  ];
}
