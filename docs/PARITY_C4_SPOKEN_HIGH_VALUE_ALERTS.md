# P-C4 — Spoken High-Value Alerts

## Parity row

`spoken_high_value_alerts` in `config/parity-snapshot.json`

## Verification method (from ledger)

End-to-end proof: high-severity signal or pending approval becomes spoken alert
only when privacy and presence settings allow.

## v1 scope

### In scope

- `spoken_alert_policy.py` eligibility on `/api/briefing` (approvals, interruptive
  watch rules, privacy/spoken toggles).
- Persisted `spoken_alerts_enabled` toggle in OperatorPresenceSettingsPanel.
- `spoken-alert-delivery.ts` voice-deck hook with browser TTS fallback and session
  dedupe.
- Contract checker: `scripts/verify/check_spoken_alert_policy.py`

### Acceptable v1 degradation

- Browser `SpeechSynthesis` is the default delivery path.
- Voice deck hook is registered API only; full Vue voice deck lands in P-D5.

### Out of scope

- Hands-free voice command loop
- Background mobile listening
- Desktop companion runtime integration

## Gate

```bash
npm run verify:parity-c4
```

## Promotion

On gate pass, update:

- `config/parity-snapshot.json` → `spoken_high_value_alerts.status = verified`
- `docs/planning/PARITY_LEDGER.md` snapshot table
- `config/parity-closure-order.json` → `P-C4.status = done`

Phase C complete after P-C4; next work enters Phase D platform blockers.
