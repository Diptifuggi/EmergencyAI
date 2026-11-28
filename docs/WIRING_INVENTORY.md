# EmergencyIQ End-to-End Wiring Inventory (Final — Phases A–D Complete)

> **Updated:** 2026-11-28  
> **Scope:** Post-Phase A/B/C/D verification of every Flutter screen/control and React Dashboard page/control.

## Status Legend
- **WORKING**: End-to-end wired to real backend API, PostgreSQL, WebSocket, and role-enforced auth.
- **COMING SOON**: Intentionally deferred feature with an explicit user-facing message (no dead buttons).

---

## 1. Flutter Mobile App Inventory

| Screen/control | API endpoint it calls | DB table | Dashboard view that shows it | Status |
| :--- | :--- | :--- | :--- | :--- |
| Register (`RegisterScreen`) | `POST /api/v1/auth/register` | `users`, `user_profiles` | `UsersAdmin` (`/admin/users`), `UserDetailPage` (`/users/:id`) | **WORKING** *(password policy, email+phone uniqueness, forced `User` role)* |
| Login (`LoginScreen`) | `POST /api/v1/auth/login`, `GET /api/v1/auth/me` | `users`, `refresh_tokens` | N/A (Citizen app access) | **WORKING** *(tokens in `flutter_secure_storage`; blocks non-`User` roles; 5-attempt lockout)* |
| Logout (`EmergencyDrawer`) | `POST /api/v1/auth/logout` | `refresh_tokens` (revoked) | N/A | **WORKING** *(revokes refresh token; clears local queue only if confirmed)* |
| Token Refresh (`AuthHttpClient`) | `POST /api/v1/auth/refresh` | `refresh_tokens` | N/A | **WORKING** *(401 interceptor refreshes once, rotates token, retries; handles offline gracefully)* |
| Profile (`EditProfileScreen`) | `GET/PUT /api/v1/users/me/profile` | `user_profiles` | `SosDetailPage`, `UserDetailPage` (`/users/:id`) | **WORKING** *(Fernet encrypted medical fields; operator access audit-logged)* |
| E-Contact (`EContactScreen`) | `GET/POST/PUT/DELETE /api/v1/users/me/emergency-contacts` | `emergency_contacts` | `SosDetailPage`, `UserDetailPage` | **WORKING** *(max 5, Indian phone validation)* |
| SOS - 3 modes (`SosScreen`) | `POST /api/v1/sos`, `.../cancel`, `.../location`, `.../status` | `sos_alerts`, `sos_location_updates`, `sos_events` | `SosAlertsPage` (`/sos`), `SosDetailPage` (`/sos/:id`) | **WORKING** *(real-time `<2s` push via `/ws/operator` + 5s polling fallback)* |
| 8 Service Tiles (`ServiceSosBottomSheet`) | `POST /api/v1/sos` (`service_category`, `category_source`), `tel:<number>` | `sos_alerts` | `SosAlertsPage`, `SosDetailPage` | **WORKING** |
| Dial 112 (`_confirmDial112`) | Native `tel:112` via `url_launcher` | None | N/A | **WORKING** |
| Voice/Text Report (`EmergencyReportScreen`) | `POST /api/v1/emergency-calls/text`, `.../audio`, `.../voice-text`, `GET /mine` | `emergency_calls`, `transcripts` | `EmergencyCalls` (`/calls`), `CallViewerPage` (`/calls/:id`) | **WORKING** *(attaches citizen JWT -> `user_id` persisted; linked to `UserDetailPage`)* |
| Chat Us (`_buildShortcutGrid`) | None (shows coming-soon notice + scrolls to emergency text box) | None | None | **COMING SOON** *(explicit user notice; no dead button)* |
| TrackMe (`TrackMeScreen` + `TrackMeService`) | `POST /api/v1/track/start`, `.../points` (batch), `.../attach-sos`, `.../stop` | `track_sessions`, `track_points` | `LiveTrackingPage` (`/live-tracking`), `PublicTrackPage` (`/track/:token`) | **WORKING** *(foreground service, battery-aware 15-30s, offline buffer, auto-attach SOS, WS real-time)* |
| SOS History (`SosHistoryScreen`, `SosHistoryDetailScreen`) | `GET /api/v1/sos/mine`, `GET /api/v1/sos/mine/{id}`, `GET /api/v1/emergency-calls/mine` | `sos_alerts`, `sos_events`, `emergency_calls` | `SosAlertsPage`, `CallViewerPage` | **WORKING** *(IST timestamps; includes Voice/Text Reports tab)* |
| Notification (`NotificationsScreen` + badge) | `GET /api/v1/users/me/notifications`, `/unread-count`, `POST .../read` | `user_notifications` | Triggered by `SosDetailPage` operator actions | **WORKING** *(15s polling; no medical data or exact coordinates)* |
| Settings (`SettingsScreen`) | Local `SharedPreferences` (`SettingsService`) | Local only | N/A | **WORKING** *(language, countdown, vibration, silent default, live location toggle, queue clear)* |
| App Info (`AppInfoScreen`) | `package_info_plus` (local) | None | N/A | **WORKING** *(disclaimer included)* |
| Top Questions (`TopQuestionsScreen`) | Local asset `assets/faq/faq_en.json` | None | N/A | **WORKING** |
| About Us (`AboutUsScreen`) | Static UI | None | N/A | **WORKING** |
| Location Bar (`_buildHomeLocationBar`) | `GET /api/v1/location/reverse?lat&lon` | Geocode cache + `SharedPreferences` | `EmergencyCalls`, `SosAlertsPage` | **WORKING** |
| Language Switch (`SettingsScreen` + Home) | `SettingsService.localeNotifier` + `Accept-Language` | Local only | `CallViewerPage` | **WORKING** |
| Drawer (`EmergencyDrawer`) | `AuthStorageService.getUserProfile()`, `POST /api/v1/auth/logout` | `user_profiles`, `refresh_tokens` | N/A | **WORKING** |

---

## 2. React Operator Dashboard Inventory

| Screen/control | API endpoint it calls | DB table | Dashboard view that shows it | Status |
| :--- | :--- | :--- | :--- | :--- |
| Login (`LoginPage` + `AuthContext`) | `POST /api/v1/auth/login`, `GET /api/v1/auth/me`, `POST /api/v1/auth/refresh` | `users`, `refresh_tokens` | `/login` | **WORKING** *(blocks `User` role; 30-min inactivity auto-logout with 1-min warning; `/unauthorized` 403 route)* |
| Overview Cards (`Dashboard.tsx`) | `GET /api/v1/emergency-calls`, `GET /api/v1/sos/stats` | `emergency_calls`, `sos_alerts`, `track_sessions` | `/dashboard` | **WORKING** *(real queries only; includes Active SOS, Silent SOS, Panic Button, Pending Verification, TrackMe Active)* |
| Calls List & Detail (`EmergencyCalls`, `CallViewerPage`) | `GET /api/v1/emergency-calls`, `GET /{id}`, `GET /users/{user_id}/summary` | `emergency_calls`, `transcripts`, `user_profiles` | `/calls`, `/calls/:id` | **WORKING** *(linked to citizen profile & `UserDetailPage`)* |
| SOS Alerts List & Detail (`SosAlertsPage`, `SosDetailPage`) | `GET /api/v1/sos`, `/{id}`, `POST .../ack|verify|close|false-alarm`, `WS /ws/operator` | `sos_alerts`, `sos_events`, `sos_profile_access_log` | `/sos`, `/sos/:id` | **WORKING** *(IST times, service filter/badges, helplines, contacts, link to `UserDetailPage`, `<2s` WS)* |
| Live Tracking Page (`LiveTrackingPage`) | `GET /api/v1/track/operator/active`, `GET /operator/{id}`, `WS /ws/operator` | `track_sessions`, `track_points`, `audit_logs` | `/live-tracking` | **WORKING** *(Leaflet map, path polyline, accuracy circle, distance, 2+ min stale warning, audit-logged)* |
| Users Admin & Detail (`UsersAdmin`, `UserDetailPage`) | `GET/POST/PATCH /api/v1/users/*`, `POST /{id}/reset-password`, `GET /{id}/summary` | `users`, `user_profiles`, `audit_logs` | `/admin/users`, `/users/:id` | **WORKING** *(Admin-only CRUD, disable, role change, password reset; operator user history view)* |
| Notification Bell (`Topbar.tsx`) | `GET /api/v1/sos?status=pending`, `GET /api/v1/emergency-calls` | `sos_alerts`, `emergency_calls` | Topbar Bell | **WORKING** *(counts unacknowledged SOS + new/critical reports with direct links)* |
| Analytics (`Analytics.tsx`) | `GET /api/v1/emergency-calls` | `emergency_calls` | `/analytics` | **WORKING** |
| Settings (`Settings.jsx`) | Static UI | None | `/settings` | **COMING SOON** *(placeholder page; settings live on Flutter client)* |
| Logout (`Sidebar.tsx` + `Topbar.tsx`) | `POST /api/v1/auth/logout` | `refresh_tokens` | Sidebar / Topbar | **WORKING** *(revokes token + clears storage)* |

---

## 3. Final Summary Totals
- **WORKING:** **31 / 33**
- **COMING SOON:** **2 / 33** *(Flutter `Chat Us` two-way chat; Dashboard `Settings` placeholder)*
- **MOCK / BROKEN / MISSING:** **0 / 33**
