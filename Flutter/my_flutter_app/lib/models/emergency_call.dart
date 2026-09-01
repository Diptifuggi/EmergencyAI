class EmergencyCall {
  final String id;
  final String callType;
  final String? textContent;
  final String? language;
  final String status;
  final String priority;
  final String? audioFilePath;
  final String? originalAudioFilename;
  final String? audioContentType;
  final int? audioFileSize;
  final String? audioUrl;
  final String? transcription;
  final String? source;
  final Map<String, dynamic>? clientMetadata;
  final double? latitude;
  final double? longitude;
  final double? locationAccuracy;
  final String? locationTimestamp;
  final String? locationAddress;
  final String locationStatus;
  final bool mapSnapshotAvailable;
  final String? mapSnapshotUrl;
  final String? createdAt;
  final String? updatedAt;

  EmergencyCall({
    required this.id,
    required this.callType,
    this.textContent,
    this.language,
    required this.status,
    required this.priority,
    this.audioFilePath,
    this.originalAudioFilename,
    this.audioContentType,
    this.audioFileSize,
    this.audioUrl,
    this.transcription,
    this.source,
    this.clientMetadata,
    this.latitude,
    this.longitude,
    this.locationAccuracy,
    this.locationTimestamp,
    this.locationAddress,
    this.locationStatus = 'unavailable',
    this.mapSnapshotAvailable = false,
    this.mapSnapshotUrl,
    this.createdAt,
    this.updatedAt,
  });

  /// Tolerant parser: unknown/future API fields are ignored.
  factory EmergencyCall.fromJson(Map<String, dynamic> json) {
    return EmergencyCall(
      id: json['id'] as String,
      callType: json['call_type'] as String? ?? 'unknown',
      textContent: json['text_content'] as String?,
      language: json['language'] as String?,
      status: json['status'] as String? ?? 'unknown',
      priority: json['priority'] as String? ?? 'normal',
      audioFilePath: json['audio_file_path'] as String?,
      originalAudioFilename: json['original_audio_filename'] as String?,
      audioContentType: json['audio_content_type'] as String?,
      audioFileSize: json['audio_file_size'] as int?,
      audioUrl: json['audio_url'] as String?,
      transcription: json['transcription'] as String?,
      source: json['source'] as String?,
      clientMetadata: json['client_metadata'] is Map<String, dynamic>
          ? json['client_metadata'] as Map<String, dynamic>
          : null,
      latitude: (json['latitude'] as num?)?.toDouble(),
      longitude: (json['longitude'] as num?)?.toDouble(),
      locationAccuracy: (json['location_accuracy'] as num?)?.toDouble(),
      locationTimestamp: json['location_timestamp']?.toString(),
      locationAddress: json['location_address'] as String?,
      locationStatus: json['location_status'] as String? ?? 'unavailable',
      mapSnapshotAvailable: json['map_snapshot_available'] as bool? ??
          (json['map_snapshot_file_path'] != null),
      mapSnapshotUrl: json['map_snapshot_url'] as String?,
      createdAt: json['created_at']?.toString(),
      updatedAt: json['updated_at']?.toString(),
    );
  }
}
