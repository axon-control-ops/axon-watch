# P-C3 — Mobile Operator Cockpit Compactness

## Parity row

`mobile_operator_cockpit_compactness` in `config/parity-snapshot.json`

## Verification method (from ledger)

Responsive UI proof on compact operator surfaces using real briefing/signal DTOs.

## v1 scope

### In scope

- Viewport resize updates `viewportWidth` in the shell store and toggles
  `console-shell--mobile-compact` without reload.
- Crossing the 768px breakpoint refetches `/api/briefing` with or without
  `viewport_compact=true` so server `mobile.compact_layout` stays aligned.
- `fetchOperatorBriefing({ viewportCompact })` is explicit; callers derive the
  flag from `shouldRequestViewportCompactBriefing`.
- Foreground-only honest posture preserved (`mobile.foreground_only: true`).

### Acceptable v1 degradation

- Foreground mobile monitoring only; no background-listening claim.
- Resize refetch is briefing-only (not full bootstrap replay).

### Out of scope

- Native mobile shell / PWA packaging
- Device orientation-specific layouts beyond width breakpoint

## Gate

```bash
npm run verify:parity-c3
```

## Promotion

On gate pass, update:

- `config/parity-snapshot.json` → `mobile_operator_cockpit_compactness.status = verified`
- `docs/planning/PARITY_LEDGER.md` snapshot table
- `config/parity-closure-order.json` → `P-C3.status = done`

Next slice: **P-C4** (`spoken_high_value_alerts`).
