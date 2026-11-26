# EmergencyIQ - SOS, Silent SOS & Panic Button Architecture & Feature Guide

## 1. Executive Summary & Core Design Principles

The **EmergencyIQ SOS Suite** introduces a dedicated, high-priority emergency intake pipeline parallel to the standard Voice/Text AI pipeline. It enables citizens to trigger instantaneous distress signals (**Standard SOS**, **Silent SOS**, and **Panic Button**) without requiring any typing or voice interaction during acute emergencies.

### Critical System Rule: AI Bypass for SOS
Unlike voice calls and text reports that flow through STT, LLM extraction, and AI triage classification:
- **SOS is a PARALLEL intake path.**
- It **bypasses the AI analysis pipeline completely** to guarantee sub-second ingestion and prevent hallucinations or AI latency during life-threatening crises.
- Emergency type is designated as `silent_sos` or `unknown_emergency`.
- Every SOS alert is automatically flagged as **`urgent human verification`**.
- It is immediately dispatched to the Operator Dashboard with audio-visual pulsing indicators and SLA tracking countdowns.

---

## 2. End-to-End Data Flow Diagram

```mermaid
flowchart TD
    subgraph MobileApp["EmergencyIQ Mobile App (Flutter)"]
        A1["SOS Button (2s hold / 5s cancel)"]
        A2["Silent SOS (One-tap discreet)"]
        A3["Panic Button (3s hold)"]
        A4["Local Offline Queue (SharedPreferences)"]
        A5["GPS & Sensor Capture (Geolocator)"]
    end

    subgraph BackendFastAPI["EmergencyIQ Backend (FastAPI)"]
        B1["POST /api/v1/sos (JWT Auth, 30s Dedup, Rate Limit)"]
        B2["Fernet Encryption Engine (AES-128-CBC + HMAC)"]
        B3["Audit & Event Logger (sos_events)"]
        B4["Role-Based Access Control (Operator Dependency)"]
    end

    subgraph Database["PostgreSQL Storage (Alembic)"]
        C1[("user_profiles\n(Allergies & History Encrypted)")]
        C2[("sos_alerts\n(Snapshot Encrypted)")]
        C3[("sos_location_updates\n(Live GPS breadcrumbs)")]
        C4[("sos_events\n(Audit Timeline)")]
        C5[("sos_profile_access_log\n(Operator View Log)")]
    end

    subgraph Dashboard["Operator Dashboard (React + Leaflet)"]
        D1["Sidebar SOS Badge (Pulsing Count)"]
        D2["SOS Alerts Table (Auto-poll 5s, SLA Timer)"]
        D3["SOS Detail / Map View (Live Marker, Leaflet)"]
        D4["Operator Actions (Ack, Verify, Close, False Alarm)"]
        D5["Decrypted Profile Drawer (Logged Access)"]
    end

    subgraph AIPipeline["Standard Voice/Text Pipeline (BYPASSED FOR SOS)"]
        E1["Sarvam / Whisper STT"]
        E2["Gemini / LLM Triage & Category Extraction"]
        E3["Emergency Calls Table"]
    end

    %% Flow connections
    A1 -->|Trigger| A5
    A2 -->|Trigger| A5
    A3 -->|Trigger| A5
    A5 -->|Payload| A4
    A4 -->|Exponential Backoff HTTP POST| B1

    B1 -->|Snapshot User Profile| C1
    B1 -->|Encrypt snapshot| B2
    B2 -->|Store encrypted snapshot| C2
    B1 -->|Log initial creation| C4

    A4 -.->|Subsequent GPS streaming| C3

    D2 -->|Polls every 5s| B1
    D3 -->|Acknowledge / Verify / Close| B4
    B4 -->|State transition| C2
    B4 -->|Audit event| C4
    D5 -->|Fetch Medical Info| B2
    B2 -->|Decrypt & Log View| C5

    %% Show bypass
    B1 -.->|X Bypasses AI Pipeline X| AIPipeline
```

---

## 3. Data Dictionary: Fields, Provenance & Encryption

| Field Name | Target Table | Data Origin / Provenance | Encryption Status | Purpose & Description |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `sos_alerts` | Client-generated UUIDv4 | Plaintext (UUID) | Unique primary key for alert tracking |
| `idempotency_key` | `sos_alerts` | Client-generated UUID/Key | Plaintext (Index) | Prevents duplicate alerts on network retries |
| `user_id` | `sos_alerts` | Backend Auth (JWT Token) | Plaintext (FK) | Reference to authenticated citizen user |
| `alert_type` | `sos_alerts` | User UI Selection | Plaintext (Enum) | `sos`, `silent_sos`, or `panic_button` |
| `status` | `sos_alerts` | System / Operator Action | Plaintext (Enum) | `pending`, `acknowledged`, `verified`, `cancelled`, `closed`, `false_alarm` |
| `latitude`, `longitude` | `sos_alerts` / `sos_location_updates` | Device GPS Sensor (`geolocator`) | Plaintext | Coordinate positioning for map dispatch |
| `accuracy_m` | `sos_alerts` / `sos_location_updates` | Device GPS Sensor | Plaintext (Float) | GPS fix precision radius in meters |
| `location_status` | `sos_alerts` | Device Location Manager | Plaintext (Enum) | `available`, `last_known`, `denied`, `unavailable` |
| `triggered_at` | `sos_alerts` | Device Hardware Clock | Plaintext (UTC) | Device timestamp when trigger was engaged |
| `received_at` | `sos_alerts` | Backend Server Clock | Plaintext (UTC) | Authoritative timestamp when alert hit server |
| `battery_pct` | `sos_alerts` | Device Battery Sensor | Plaintext (Int) | Device battery level percentage (0-100) |
| `network_type` | `sos_alerts` | Device Connectivity Manager | Plaintext (String) | Network connection type: `wifi`, `cellular`, `offline` |
| `device_id` | `sos_alerts` | Device Hardware Info | Plaintext (String) | Unique hardware or installation instance ID |
| `app_version` | `sos_alerts` | App Package Config | Plaintext (String) | Application release build version |
| `allergies` | `user_profiles` | User Input (Profile Onboarding) | **Fernet Encrypted** | Critical allergy records (e.g. penicillin, nuts) |
| `medical_history` | `user_profiles` | User Input (Profile Onboarding) | **Fernet Encrypted** | Chronic medical conditions (e.g. asthma, diabetes) |
| `profile_snapshot_encrypted` | `sos_alerts` | Backend Serialization + Encrypt | **Fernet Encrypted** | Immutable copy of user profile & contacts at alert time |
| `medical_consent` | `user_profiles` | User Checkbox Selection | Plaintext (Bool) | Citizen consent for first responders to view medical info |
| `medical_consent_at` | `user_profiles` | Backend Server Clock | Plaintext (UTC) | Timestamp when citizen agreed to emergency consent |

---

## 4. Role-Based Access Control (RBAC) & Visibility Matrix

| Feature / Data Element | Citizen (Self) | Operator | Supervisor / Admin |
| :--- | :---: | :---: | :---: |
| **Trigger SOS / Silent / Panic** | ✅ Yes | ❌ No | ❌ No |
| **View Own Active SOS Status** | ✅ Yes (polling/stream) | ❌ No | ❌ No |
| **Cancel Own SOS with Reason** | ✅ Yes | ❌ No | ❌ No |
| **Stream Live GPS Updates** | ✅ Yes | ❌ No | ❌ No |
| **Edit Own Medical Profile** | ✅ Yes | ❌ No | ❌ No |
| **View All SOS Alerts List** | ❌ 403 Forbidden | ✅ Yes (Real-time table) | ✅ Yes |
| **Acknowledge SOS Alert** | ❌ 403 Forbidden | ✅ Yes | ✅ Yes |
| **Verify Emergency with Caller** | ❌ 403 Forbidden | ✅ Yes | ✅ Yes |
| **Close Alert / False Alarm** | ❌ 403 Forbidden | ✅ Yes | ✅ Yes |
| **Decrypt Medical Profile Snapshot** | ❌ 403 Forbidden | ✅ Yes (Access logged) | ✅ Yes (Access logged) |
| **View Audit Trail & Events** | ❌ 403 Forbidden | ✅ Yes | ✅ Yes |
| **View Global SOS Statistics** | ❌ 403 Forbidden | ✅ Yes | ✅ Yes |

---

## 5. Privacy, Consent & Audit Compliance

### 5.1 Exact In-App Consent Notice
During user profile registration or editing within the Flutter application, users must explicitly review and toggle the medical disclosure consent:

> *"I authorize emergency medical responders and dispatchers to access my medical conditions, allergy history, and emergency contacts solely during active SOS alerts for immediate life-safety care."*

- If consent is unchecked (`false`), medical history and allergies are not included in the decrypted medical snapshot presented to operators.
- `medical_consent_at` records the exact ISO-8601 UTC timestamp of citizen consent.

### 5.2 Encryption at Rest Architecture
- Sensitive health fields (`allergies`, `medical_history`, and the alert `profile_snapshot_encrypted`) are encrypted using **Fernet symmetric encryption** (AES-128 in CBC mode with HMAC-SHA256 authenticated encryption).
- The key is derived from the environment variable `PROFILE_ENCRYPTION_KEY`. The backend will securely fail to start if this key is missing or improperly formatted.
- Database administrators or unauthorized database readers with direct SQL access cannot view medical data in plaintext.

### 5.3 Audit & Access Logging Policy
- Every time an emergency dispatcher/operator opens or views the citizen's medical profile drawer, an immutable row is recorded in `sos_profile_access_log`:
  - `alert_id`: The emergency incident UUID.
  - `operator_id`: The UUID of the authenticated operator.
  - `accessed_at`: Authoritative server UTC timestamp.
- Internal application logs strictly enforce confidentiality: **phone numbers, GPS coordinates, and medical fields are never logged at `INFO` or below levels.**

---

## 6. Known Limitations & Roadmap (Phase 2 & 3)

1. **No SMS / GSM Fallback in Phase 1**:
   - Alerts currently require active HTTP/cellular data or Wi-Fi connectivity. If internet connectivity is completely lost, the mobile app queues the alert locally in `SharedPreferences` with exponential backoff retries until connectivity resumes. SMS fallback via cellular gateway is scheduled for Phase 2.
2. **Lockscreen / Hardware Volume Key Triggers on iOS**:
   - Background hardware key interception (e.g. triple-clicking power or volume buttons while the device is locked) is restricted by Apple iOS sandbox policies. The present version requires opening the EmergencyIQ app or utilizing widget/accessibility shortcuts.
3. **No Direct 112 / PSAP CAD Integration**:
   - SOS alerts currently route directly into the EmergencyIQ Operator Command Dashboard. Forwarding directly to national PSAP CAD (Computer-Aided Dispatch) via CAP (Common Alerting Protocol) or standard 112 interfaces will be deployed in subsequent enterprise integrations.
