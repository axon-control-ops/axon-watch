# Android background wake — evidence checklist

Complete and attach artifacts **before** releasing background listen to operators. The PWA stays foreground-only; only this native companion may claim background wake.

## Lock screen / process survival

- [ ] Foreground service notification remains visible with screen off / lock screen engaged
- [ ] Service restarts after swipe-away from recents while wake is armed (or documents OEM limits)
- [ ] Cold boot / reboot: wake does **not** auto-arm without operator opt-in after enrollment
- [ ] Doze / App Standby: listening still meets declared SLA, or documented deferral behavior

## Audio focus & capture

- [ ] Privacy mute stops local capture immediately (no ring-buffer fill while muted)
- [ ] Pre-wake audio never leaves device (network capture / proxy evidence of zero upload pre-wake)
- [ ] Concurrent media / call: audio focus policy documented; no silent capture during active call unless explicitly allowed
- [ ] RECORD_AUDIO runtime permission denied path: service does not claim “listening”
- [ ] POST_NOTIFICATIONS denied (API 33+): operator is blocked from arming with a clear error

## Battery / thermal

- [ ] 8h idle listen battery delta measured on reference device (pixel-class + one OEM)
- [ ] No unbounded wake locks outside FGS contract
- [ ] Thermal throttling does not corrupt mute / revoke state

## Enrollment & revocation

- [ ] Enroll via `POST /api/devices/enroll` persists device id used by wake arming
- [ ] `POST /api/devices/{id}/revoke` disarms wake within defined SLA and stops FGS
- [ ] Revoked device cannot re-arm until re-enrolled
- [ ] List endpoint reflects active vs revoked status

## Functional stubs → real model gate

- [ ] Stub wake callbacks replaced or gated behind build flavor before production
- [ ] Proprietary / third-party wake model license review complete (if any)
- [ ] Converse / briefing / TTS paths only activate post-wake + active enrollment

## Sign-off

| Role | Name | Date | Notes |
| --- | --- | --- | --- |
| Operator | | | |
| Security / privacy | | | |
| Mobile | | | |
