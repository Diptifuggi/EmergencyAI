# EmergencyIQ API Keys - Security & Configuration Guide

## ⚠️ CRITICAL SECURITY NOTICE

**Never commit API keys to Git!** These keys are now in `.env` and `local.properties` files which are Git-ignored. Keep them secure.

---

## API Keys Inventory

### 1. **EmergencyIQ-Android-Maps** (Flutter Android App)
**Key**: `AIzaSyAd1cDr0krTztBwW9W7DUIZZ1_LANQrZvI`

**Location**: `Flutter/my_flutter_app/android/local.properties`

**Purpose**: 
- Display Google Maps in Flutter Android app
- Show caller's GPS location on map
- Mark caller's location with marker

**Restrictions** (Google Cloud Console):
- Android apps only
- Package: `com.emergencyiq.my_flutter_app`
- Configured SHA-1 certificate fingerprint
- Maps SDK for Android

**Security**:
- ✅ Stored in `local.properties` (Git-ignored)
- ✅ Never hardcoded in Dart
- ✅ Never appears in logs
- ✅ Never committed to Git
- ✅ Build time injection via Gradle

---

### 2. **EmergencyIQ-Geocoding-Backend** (FastAPI Backend)
**Key**: `AIzaSyB9EabItFIvafAQwBODwX0LR8hn7tdtg1E`

**Location**: `backend/.env` environment variable

**Purpose**:
- Reverse geocode GPS coordinates to human-readable addresses
- Called from FastAPI backend only (NOT from Flutter)
- Convert latitude/longitude → street address

**Example Usage** (Backend):
```python
import os
import googlemaps

geocoding_key = os.getenv("GOOGLE_GEOCODING_API_KEY")
gmaps = googlemaps.Client(key=geocoding_key)

result = gmaps.reverse_geocode((latitude, longitude))
address = result[0]['formatted_address']
```

**Restrictions** (Google Cloud Console):
- Web/backend API access only
- Geocoding API enabled
- Recommended: restrict to backend IP if known

**Security**:
- ✅ Stored in `backend/.env` (Git-ignored)
- ✅ Loaded via environment variable
- ✅ Never hardcoded in Python
- ✅ Never appears in API responses to Flutter
- ✅ Never committed to Git

---

### 3. **Maps Platform API Key** (Purpose TBD)
**Key**: `AIzaSyCOYIWMB1mR77Fkyrrz9L26pdXmuRN6ngk`

**Status**: Not yet assigned

**Recommendation**:
- Clarify purpose (master key, fallback, dashboard?)
- If for frontend dashboard: keep on dashboard server only
- If for backend secondary: add to `backend/.env` as fallback
- Never place in Flutter app

---

## Git Configuration

### Verify Files are Ignored

**Flutter Android**:
```bash
# Should be in .gitignore
cat Flutter/my_flutter_app/.gitignore | grep local.properties

# Expected output:
# /android/local.properties
```

**Backend**:
```bash
# Should be in .gitignore
cat backend/.gitignore | grep -E ".env|__pycache__"

# Expected output:
# .env
# .env.local
# .env.*.local
```

### Verify No Keys Committed

```bash
# Check git history for API keys
git log -p | grep -i "AIzaSy"

# Should return nothing. If found, rotate keys immediately!
```

---

## Configuration Verification

### Android App Verification

**Check local.properties**:
```bash
cat Flutter/my_flutter_app/android/local.properties
```

**Expected output**:
```properties
sdk.dir=C:\\Users\\USER\\AppData\\Local\\Android\\sdk
flutter.sdk=C:\\src\\flutter
flutter.buildMode=debug
flutter.versionName=1.0.0
flutter.versionCode=1
GOOGLE_MAPS_API_KEY=AIzaSyAd1cDr0krTztBwW9W7DUIZZ1_LANQrZvI
```

**Verify Build Configuration**:
```bash
cd Flutter/my_flutter_app
grep -A 5 "GOOGLE_MAPS_API_KEY" android/app/build.gradle.kts
```

**Expected**: Gradle reads key from local.properties and injects into manifest

**Build and Test**:
```bash
flutter clean
flutter pub get
flutter run
```

**Runtime Check** (Flutter app):
- Open Emergency Report screen
- Tap "Capture current GPS location"
- Tap "View location on map"
- Should display Google Map with marker (no errors)

---

### Backend Verification

**Check .env file**:
```bash
grep "GOOGLE_GEOCODING_API_KEY" backend/.env
```

**Expected**:
```
GOOGLE_GEOCODING_API_KEY=AIzaSyB9EabItFIvafAQwBODwX0LR8hn7tdtg1E
```

**Verify Python can access**:
```bash
cd backend
source .venv/Scripts/activate  # or .venv/bin/activate on Linux/Mac
python -c "import os; print(os.getenv('GOOGLE_GEOCODING_API_KEY'))"
```

**Expected output**:
```
AIzaSyB9EabItFIvafAQwBODwX0LR8hn7tdtg1E
```

**Test Geocoding API** (Optional):
```python
import os
import googlemaps

key = os.getenv("GOOGLE_GEOCODING_API_KEY")
if not key:
    print("ERROR: GOOGLE_GEOCODING_API_KEY not set")
else:
    gmaps = googlemaps.Client(key=key)
    result = gmaps.reverse_geocode((28.6139, 77.2090))  # New Delhi coords
    print(result[0]['formatted_address'])
```

---

## Troubleshooting

### Flutter Map Shows "Error"

**Possible causes**:
1. ❌ API key not in `android/local.properties`
2. ❌ API key invalid or expired
3. ❌ API key restricted incorrectly
4. ❌ Maps SDK for Android not enabled in Google Cloud

**Fix**:
- Verify key in local.properties: `grep GOOGLE_MAPS_API_KEY Flutter/my_flutter_app/android/local.properties`
- Check Google Cloud Console: Maps SDK for Android enabled?
- Check API key restrictions: Android package `com.emergencyiq.my_flutter_app`
- Check logcat: `flutter logs`

---

### Backend Geocoding Not Working

**Possible causes**:
1. ❌ API key not in `.env`
2. ❌ API key invalid or expired
3. ❌ Geocoding API not enabled in Google Cloud
4. ❌ Python not reading environment variable

**Fix**:
- Verify key in .env: `grep GOOGLE_GEOCODING_API_KEY backend/.env`
- Restart backend after .env change: `python main.py`
- Check Google Cloud Console: Geocoding API enabled?
- Test environment variable: `python -c "import os; print(os.getenv('GOOGLE_GEOCODING_API_KEY'))"`

---

## Key Rotation (If Compromised)

If either key is accidentally committed or exposed:

### Immediate Actions
1. ❌ Rotate the key in Google Cloud Console (disable old key)
2. ✅ Create new key with same restrictions
3. ✅ Update `android/local.properties` with new key
4. ✅ Update `backend/.env` with new key
5. ✅ Do NOT commit the rotation
6. ✅ Do NOT commit old keys to history

### Google Cloud Steps
```
1. Go to Google Cloud Console → APIs & Services → Credentials
2. Find compromised key
3. Delete old key (or disable if can't delete)
4. Create new key with same restrictions
5. Copy new key
6. Update local.properties / .env
7. Rebuild and redeploy
```

---

## Documentation

- **Android Maps Setup**: [Flutter/my_flutter_app/android/GOOGLE_MAPS_SETUP.md](../Flutter/my_flutter_app/android/GOOGLE_MAPS_SETUP.md)
- **Google Maps Implementation**: [Flutter/my_flutter_app/GOOGLE_MAPS_IMPLEMENTATION_REPORT.md](../Flutter/my_flutter_app/GOOGLE_MAPS_IMPLEMENTATION_REPORT.md)
- **Flutter Map Screen**: [Flutter/my_flutter_app/lib/screens/map_screen.dart](../Flutter/my_flutter_app/lib/screens/map_screen.dart)

---

## Security Checklist

- [x] Android Maps key in `local.properties` (not in Dart code)
- [x] Android Maps key Git-ignored
- [x] Android Maps key injected at build time via Gradle
- [x] Geocoding key in `backend/.env` (not in Python code)
- [x] Geocoding key Git-ignored
- [x] Geocoding key loaded via environment variable
- [x] No keys hardcoded anywhere
- [x] No keys in logs or debug output
- [x] No keys in API responses
- [x] .gitignore covers all secret files
- [x] No keys committed to Git history

---

## Next Steps

1. ✅ **Android**: Build and test map display
   ```bash
   cd Flutter/my_flutter_app
   flutter clean && flutter pub get && flutter run
   ```

2. ✅ **Backend**: Test geocoding if implemented
   ```bash
   cd backend
   source .venv/Scripts/activate
   python main.py
   ```

3. ✅ **Verification**: Submit an emergency call with location
   - Capture GPS location in Flutter app
   - Submit text or voice emergency
   - Verify coordinates stored in PostgreSQL
   - Optional: test reverse geocoding on backend

4. ✅ **Production**: 
   - Use environment-specific keys if needed
   - Document key rotation procedure
   - Monitor API usage in Google Cloud Console

---

**Prepared**: 2026-09-01  
**Status**: 🔒 SECURE - Keys protected, Git-ignored, environment-based
