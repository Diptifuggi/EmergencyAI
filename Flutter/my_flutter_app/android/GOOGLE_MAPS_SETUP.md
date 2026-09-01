# Google Maps API Key Configuration

## Android Maps API Key Setup

The Google Maps Android Maps API key is required to display maps in the Android app.

### Where to Place the Key

Edit or create the file: `android/local.properties` (same level as `build.gradle.kts`)

### Configuration

Add this line to `android/local.properties`:

```
GOOGLE_MAPS_API_KEY=YOUR_ACTUAL_API_KEY_HERE
```

Replace `YOUR_ACTUAL_API_KEY_HERE` with your actual EmergencyIQ-Android-Maps API key from Google Cloud Console.

### Important Security Notes

- ✅ `local.properties` is in `.gitignore` and will NOT be committed to Git
- ✅ The API key is restricted to Android package: `com.emergencyiq.my_flutter_app`
- ✅ The API key is restricted to the configured SHA-1 certificate fingerprint
- ✅ Never paste the raw API key directly into Dart code or other source files
- ✅ Never commit the actual key value to Git

### Build Process

During the Android build:
1. Gradle reads `local.properties`
2. Extracts the `GOOGLE_MAPS_API_KEY` value
3. Injects it into `AndroidManifest.xml` via manifest placeholders
4. The Maps SDK for Android picks up the key at runtime

### Verification

After placing the key in `local.properties`:

```bash
cd Flutter/my_flutter_app
flutter clean
flutter pub get
flutter build apk  # or flutter run
```

If the key is invalid or missing, the map will display an error and logs will show:
```
E/Google Maps Android API: Authorization failure
```

### Multiple Keys

This project uses TWO separate API keys:

| Key Name | Purpose | Location | Restricted To |
|----------|---------|----------|----------------|
| `EmergencyIQ-Android-Maps` | Flutter Android app map display | `android/local.properties` | Android package + SHA-1 |
| `EmergencyIQ-Geocoding-Backend` | FastAPI backend geocoding | FastAPI `.env` file | Backend server only |

**NEVER** place the `EmergencyIQ-Geocoding-Backend` key in Flutter or Android.

### Troubleshooting

- **Map shows "Error"**: API key may be invalid, missing, or not restricted properly. Check Google Cloud Console.
- **Build fails to find `local.properties`**: Create it manually with the key line above.
- **Map still gray/blank**: Check logcat output for "Authorization failure" errors.
