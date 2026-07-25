# P-C1 — KAIRO Persona Operator Copy

## Parity row

`kairo_persona_operator_copy` in `config/parity-snapshot.json`

## Verification method (from ledger)

Contract test on persona module output; UI/voice proof that tone changes do not
alter run/signal truth.

## v1 scope

### In scope

- Persisted operator presence settings via `GET/PUT /api/operator-presence/settings`
  (SQLite-backed singleton row).
- `/api/briefing` `operator_presence.settings` reflects persisted values.
- `operator_persona_enabled=false` switches to neutral copy without changing
  `notice`, `advise`, pending approval counts, or signal truth.
- Console-web settings panel persists locally and syncs to control-plane; toggling
  persona refetches briefing.

### Acceptable v1 degradation

- Single persona toggle in settings panel (not full JARVIS identity options).
- Browser TTS and spoken-alert policy unchanged in this slice (P-C4).

### Out of scope

- `packages/prompt-contracts` extraction
- Full voice-deck persona variants

## Gate

```bash
npm run verify:parity-c1
```

## Promotion

On gate pass, update:

- `config/parity-snapshot.json` → `kairo_persona_operator_copy.status = verified`
- `docs/planning/PARITY_LEDGER.md` snapshot table
- `config/parity-closure-order.json` → `P-C1.status = done`

Next slice: **P-C2** (`executive_operator_rhythm`).
