# VAXON Android companion (scaffold)

Native Kotlin / Jetpack Compose companion for **Continuity VAXON Parity**.

## Role vs PWA

| Surface | Capability |
| --- | --- |
| Console **PWA** | Remains **foreground_only** voice. No reliable background mic / wake. |
| **This native app** | The **only** supported background-listen path (foreground service + local wake stub). |

Do not treat the PWA as a substitute for lock-screen or background wake.

## Privacy contract

1. **Pre-wake audio stays local.** Capture for wake detection is intended as an on-device ring buffer only.
2. **Never upload pre-wake PCM.** Upload / STT may begin only *after* a confirmed wake (and enrollment is active).
3. **Privacy mute** disarms capture hooks while the persistent notification can remain (service still visible).
4. **Revocation** from the control plane must disarm background wake before release (see evidence checklist).

This scaffold ships a **stub** local wake (`StubLocalWakeDetector`) that logs and exposes callbacks. There is **no** proprietary wake model yet.

## Module layout

```
apps/vaxon-android/
  settings.gradle.kts
  build.gradle.kts
  gradle.properties
  app/build.gradle.kts
  app/src/main/...
  docs/
```

Screens (Compose stubs): Enrollment, Privacy/Mic status, Conversation (orb placeholder), Approvals, Receipts.

Control-plane client stubs (`DeviceEnrollmentClient`):

- `POST /api/devices/enroll`
- `POST /api/devices/{id}/revoke`
- `GET /api/devices`
- `POST /api/kairo/converse`
- `GET /api/briefing`
- `POST /api/kairo/tts`

Default emulator base URL: `http://10.0.2.2:8787` (override via `CONTROL_PLANE_BASE_URL` in `app/build.gradle.kts`).

## Build instructions

CI may not have the Android SDK. Build on a machine with Android Studio / SDK + JDK 17:

```bash
cd apps/vaxon-android

# One-time: install wrapper jar if missing
# gradle wrapper --gradle-version 8.9

./gradlew :app:assembleDebug
# or, if wrapper binary is not checked in yet:
gradle :app:assembleDebug
```

Open the folder in Android Studio → Sync → Run on emulator/device.

Required local tooling:

- Android SDK Platform **35**
- Build-Tools matching AGP **8.7.x**
- JDK **17**

## Evidence before release

Complete [ANDROID_BACKGROUND_WAKE_EVIDENCE.md](./ANDROID_BACKGROUND_WAKE_EVIDENCE.md) before shipping background listen to operators. Enrollment + revocation + privacy mute are release gates, not polish.
