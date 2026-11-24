# EmergencyIQ Flutter client

The Flutter app connects to the FastAPI backend on port `8000`. It checks
`/api/v1/health` at startup, discovers the backend on a local Wi-Fi network
when possible, and retries when the connection banner is tapped.

## Start the backend

From the repository root, open a terminal and run:

```powershell
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Confirm the API responds before launching Flutter:

```powershell
Invoke-WebRequest http://127.0.0.1:8000/api/v1/health
```

## Run the Flutter app

In another terminal:

```powershell
cd Flutter\my_flutter_app
flutter pub get
flutter run
```

Backend addresses depend on where Flutter runs:

| Flutter target | Backend address |
| --- | --- |
| Windows desktop or web on the same PC | `http://127.0.0.1:8000` |
| Android emulator | `http://10.0.2.2:8000` |
| Android device over USB | Run `adb reverse tcp:8000 tcp:8000`; use `http://127.0.0.1:8000` |
| Physical device over Wi-Fi | Use the PC's LAN IP, e.g. `http://192.168.1.25:8000` |

For a physical device or a non-default backend host, set the backend explicitly
at launch:

```powershell
flutter run --dart-define=API_BASE_URL=http://192.168.1.25:8000
```

Replace the example address with the PC's current LAN IP. The device and PC
must be on a network that permits device-to-device connections. Allow inbound
TCP port `8000` through the PC firewall on private networks if prompted.

The app's connection banner reports whether the health endpoint is reachable
and displays the selected URL. Tap it to retry discovery. Emergency reports,
audio/transcription, and map snapshots use the versioned `/api/v1` routes.
