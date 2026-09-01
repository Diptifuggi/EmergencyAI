# Flutter Project Analysis - EmergencyIQ

## 1. PUBSPEC.YAML - DEPENDENCIES

### Location & Map-Related Packages (Already Present)
- **geolocator: ^13.0.2** - GPS/location services with permission handling
- **flutter_map: ^7.0.2** - Map widget using OpenStreetMap tiles
- **latlong2: ^0.9.1** - LatLng coordinates support
- **permission_handler: ^11.3.1** - Runtime permissions management

### Other Key Dependencies
- **http: ^1.2.2** - HTTP client for API calls
- **record: ^6.0.0** - Audio recording
- **speech_to_text: ^7.0.0** - Speech-to-text recognition
- **connectivity_plus: ^6.0.5** - Network connectivity detection
- **network_info_plus: ^6.0.2** - WiFi info (used in backend discovery)
- **shared_preferences: ^2.3.2** - Local storage for cached URL
- **path_provider: ^2.1.4** - File system paths
- **path: ^1.9.0** - Path utilities
- **cupertino_icons: ^1.0.8** - iOS icons

---

## 2. LIB/ DIRECTORY STRUCTURE

```
lib/
├── main.dart                          # App entry point
├── core/
│   ├── language/
│   │   ├── emergency_language_option.dart
│   │   └── language_mapper.dart       # Maps UI language → API codes (en/hi/gu/mr)
│   └── network/
│       ├── api_client.dart            # HTTP client wrapper
│       └── backend_discovery.dart     # Auto-discovery of FastAPI backend
├── models/
│   ├── emergency_call.dart            # Main emergency data model
│   └── emergency_location.dart        # Location data model
├── services/
│   ├── emergency_api_service.dart     # API calls to FastAPI
│   └── location_service.dart          # GPS/location retrieval
├── screens/
│   └── emergency_report_screen.dart   # Main UI screen
└── widgets/
    ├── app_colors.dart                # Color constants
    └── emergency_location_card.dart   # Map display widget
```

---

## 3. ANDROID BUILD CONFIGURATION

### Build System: **Kotlin DSL** (Modern)
- `build.gradle.kts` (root level)
- `app/build.gradle.kts` (app level)
- `settings.gradle.kts`

### Android Versions (from app/build.gradle.kts)
```
compileSdk = flutter.compileSdkVersion  (uses Flutter's default)
minSdk = maxOf(flutter.minSdkVersion, 24)
targetSdk = flutter.targetSdkVersion    (uses Flutter's default)
```
- **Java Version**: 17
- **Kotlin JVM Target**: 17

### AndroidManifest.xml Permissions
✅ **Location Permissions Already Configured:**
```xml
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION"/>
<uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION"/>
```

✅ **Other Essential Permissions:**
- `android.permission.INTERNET` - API calls
- `android.permission.ACCESS_NETWORK_STATE` - Network detection
- `android.permission.ACCESS_WIFI_STATE` - WiFi detection
- `android.permission.RECORD_AUDIO` - Audio recording
- `android.permission.MODIFY_AUDIO_SETTINGS` - Audio control

### Application Configuration
- **App Name**: EmergencyIQ
- **Package ID**: com.emergencyiq.my_flutter_app
- **Activity**: MainActivity (singleTop launchMode)
- **Clear Text Traffic**: Enabled (usesCleartextTraffic="true")

---

## 4. EXISTING LOCATION/PERMISSION/GPS CODE

### LocationService ([lib/services/location_service.dart](lib/services/location_service.dart))

**Functionality:**
- Checks if location services are enabled
- Requests location permission (handles all permission states)
- Gets high-accuracy GPS position with 10-second timeout
- Returns `EmergencyLocation` object

**Exception Handling:**
```dart
// Throws LocationServiceException for:
- Location services disabled
- Permission denied
- Permission permanently denied
```

**Output:**
```dart
class EmergencyLocation {
  final double latitude;
  final double longitude;
  final double accuracy;       // GPS accuracy in meters
  final DateTime timestamp;
}
```

### Permission Handling ([lib/screens/emergency_report_screen.dart](lib/screens/emergency_report_screen.dart))

**Microphone Permission Request:**
```dart
final permission = await Permission.microphone.request();
// Used for: Speech recognition & audio recording
```

---

## 5. EXISTING API SERVICE FILES

### EmergencyApiService ([lib/services/emergency_api_service.dart](lib/services/emergency_api_service.dart))

**Three Submission Endpoints:**

#### 1. **Text Emergency** (`POST /api/v1/emergency-calls/text`)
```dart
submitTextEmergency({
  required String text,
  required String language,        // en/hi/gu/mr
  double? latitude,
  double? longitude,
  double? locationAccuracy,
  DateTime? locationTimestamp,
  Map<String, dynamic>? clientMetadata,
})
```

#### 2. **Voice + Text** (`POST /api/v1/emergency-calls/voice-text`) - **PREFERRED**
```dart
submitVoiceAndText({
  required File audioFile,
  required String transcription,
  required String language,
  double? latitude,
  double? longitude,
  double? locationAccuracy,
  DateTime? locationTimestamp,
  Map<String, dynamic>? clientMetadata,
})
```
Uses multipart/form-data for file upload

#### 3. **Audio Only** (`POST /api/v1/emergency-calls/audio`)
```dart
submitAudioEmergency({
  required File audioFile,
  required String language,
  String? transcription,           // Optional
  double? latitude,
  double? longitude,
  double? locationAccuracy,
  DateTime? locationTimestamp,
  Map<String, dynamic>? clientMetadata,
})
```

#### 4. **List Emergencies** (`GET /api/v1/emergency-calls/`)
```dart
listEmergencyCalls({
  int limit = 50,
  int offset = 0,
})
```

### Data Models

#### EmergencyCall Model
**Full list of fields returned from API:**
- `id` - Unique identifier
- `callType` - Type of call (text/audio/voice-text)
- `textContent` - Text message
- `language` - Language code
- `status` - Current status
- `priority` - Priority level
- `audioFilePath`, `audioUrl`, `transcription`
- **Location data:**
  - `latitude`, `longitude`
  - `locationAccuracy` (meters)
  - `locationTimestamp`
  - `locationAddress` (reverse geocoded)
  - `locationStatus` (available/unavailable)
- `clientMetadata` - Custom metadata dict
- `source` - "flutter"
- `createdAt`, `updatedAt`

#### EmergencyLocation Model
```dart
class EmergencyLocation {
  final double latitude;
  final double longitude;
  final double accuracy;      // GPS accuracy in meters
  final DateTime timestamp;
}
```

---

## 6. BACKEND DISCOVERY MECHANISM

### BackendDiscovery ([lib/core/network/backend_discovery.dart](lib/core/network/backend_discovery.dart))

**Auto-discovery order:**
1. Build-time environment variable: `API_BASE_URL`
2. Cached URL from SharedPreferences
3. USB localhost (127.0.0.1:8000 via adb reverse)
4. Emulator host (10.0.2.2:8000)
5. **WiFi subnet scan** - Parallel scan of `/api/v1/health` endpoint

**Configuration:**
- **Port**: 8000
- **Health check endpoint**: `/api/v1/health`
- **Connection timeout**: 900ms
- **Scan batch size**: 24 IPs at a time

**Caching:**
- Stores working URL in SharedPreferences (key: `emergencyiq_api_base_url`)
- Re-checks health on app startup
- Refreshes on WiFi reconnection events

---

## 7. LANGUAGE SUPPORT

### LanguageMapper ([lib/core/language/language_mapper.dart](lib/core/language/language_mapper.dart))

**Valid EmergencyIQ API Language Codes:**
- `en` - English
- `hi` - Hindi
- `gu` - Gujarati
- `mr` - Marathi

**Conversion Logic:**
- Maps UI language selection → API codes
- Handles language prefix extraction (e.g., "en-IN" → "en")
- Validates against opaque STT engine IDs
- Prevents sending device speech engine identifiers to API

---

## 8. EMERGENCY REPORT SCREEN - FULL FLOW

### Main UI Features ([lib/screens/emergency_report_screen.dart](lib/screens/emergency_report_screen.dart))

**Language Selection:**
- Dropdown for: English, Hindi, Gujarati, Marathi
- Auto-selects matching STT locale

**Text Emergency:**
1. Type or speak emergency message (via STT)
2. Click "Capture current GPS location"
3. Submit text with GPS data

**Voice/Audio Emergency:**
1. Record audio (stores as M4A, 128kbps, 44100 Hz)
2. Optional transcription via STT
3. Submit audio + transcription + GPS

**State Management:**
- Records current location
- Formats latitude/longitude to 7 decimal places
- Tracks GPS accuracy
- Stores location error (if any) in clientMetadata
- Shows successful submission with call ID and status

**Client Metadata Sent:**
```dart
{
  'platform': 'flutter',
  'recorded_at': DateTime.now().toIso8601String(),
  'selected_language': _selectedLanguage.displayName,
  'stt_locale': _activeSttLocale?.localeId,
  'location_error': 'error message if location failed'
}
```

---

## 9. MAP DISPLAY WIDGET

### EmergencyLocationCard ([lib/widgets/emergency_location_card.dart](lib/widgets/emergency_location_card.dart))

**Features:**
- Displays map of submitted emergency location
- Uses OpenStreetMap tiles
- Configurable tile URL via `MAP_TILE_URL` environment variable
  - Default: `http://10.0.2.2:8081/tiles/{z}/{x}/{y}.png`
- Red pin marker at location
- Shows latitude, longitude, GPS accuracy
- Shows reverse-geocoded address (if available)
- Attribution: © OpenStreetMap contributors

---

## 10. SUMMARY OF DATA FLOW

```
User Input (Text/Speech/Audio)
    ↓
LocationService.getCurrentLocation()
    ↓ (GPS + coordinates + accuracy)
EmergencyApiService.submit*Emergency()
    ↓ (HTTP POST/multipart to /api/v1/emergency-calls/*)
FastAPI Backend
    ↓ (Processes location, geocodes address, analyzes content)
Response: EmergencyCall (with server-assigned ID, status)
    ↓
UI Updates with saved call details & map
```

---

## 11. KEY INTEGRATION POINTS FOR YOUR WORK

✅ **Already in place:**
- GPS permissions & location retrieval
- Location data passed to API (latitude, longitude, accuracy, timestamp)
- Map display widget
- Backend auto-discovery for WiFi/LAN deployment
- Multi-language support
- Microphone & audio permissions

**Available for enhancement:**
- Reverse geocoding (location_address field from API)
- Real-time location tracking
- Location history
- Advanced map features (directions, routes)
- Background location updates
- Location sharing mechanisms
- Emergency hotspot/safe zone features

