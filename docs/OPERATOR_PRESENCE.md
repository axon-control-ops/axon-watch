# Operator Presence (Spoken Alerts, Persona, Mobile)

## Purpose

Thin v1 slice for the locked cutover item **Spoken alerts, persona, and mobile
presence**. Establishes canonical operator-presence projection on the briefing API
without claiming full voice-deck or background mobile listening parity.

## Surfaces

| Layer | Responsibility |
|---|---|
| `kairo_persona.py` | Persona voice lines from briefing context |
| `spoken_alert_policy.py` | Spoken-alert eligibility (privacy, watch_rule, approvals) |
| `operator_presence.py` | Assembled `operator_presence` block |
| `/api/briefing` | Returns `operator_presence` (+ optional `viewport_compact`) |
| `console-web` | Persona copy, spoken-alert hook, mobile compact shell class |

## `operator_presence` block

- `persona_voice_line` — KAIRO operator copy (does not alter run/signal truth)
- `presence_state` — `idle` \| `observing` \| `alerting` \| `privacy_blocked`
- `settings` — persona/spoken/mobile toggles (bootstrap defaults today)
- `spoken_alert` — `{ eligible, reason, signal_id, message }`
- `mobile` — `{ compact_layout, foreground_only: true }`

Fixture: `packages/shared-types/fixtures/operator-briefing.example.json`

## Spoken alert policy (v1)

Eligible when:

- `spoken_alerts_enabled` and not `privacy_mode`
- pending approvals exist, **or**
- top signal has interruptive `watch_rule` (`approval` / `execute`, or
  `interrupts` with `high` / `critical` severity)

Browser speech uses `SpeechSynthesisUtterance` with session dedupe — desktop
foreground only. No background listening claim.

## Mobile posture (v1)

- `GET /api/briefing?viewport_compact=true` sets `mobile.compact_layout`
- Shell adds `console-shell--mobile-compact` when viewport is narrow or flag set
- `foreground_only: true` documents honest mobile scope

## Verification

```bash
npm run verify:test7
# or
./scripts/verify/test7-operator-presence.sh
```

## Cutover status

Verified by **TEST-7**. Next locked item: **Cross-repo planning migration**.

## Not in v1 (explicit)

- Full voice command deck / hands-free loop
- Background mobile listening
- Persisted operator notification preferences UI
- `packages/prompt-contracts` extraction (Python owns policy for now)
