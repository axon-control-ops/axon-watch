# P-A4 — Signal / Inbox Consistency Cross-Surface Parity

## Parity row

`signal_inbox_consistency` in `config/parity-snapshot.json`

## Verification method (from ledger)

One signal rendered consistently across inbox, summary, and detail surfaces.

## v1 scope

### In scope

- Same `signal_id`, `severity`, `status`, `source` on:
  - `GET /api/inbox` top item
  - `GET /api/runtime/summary` `signals.top_items[0]`
  - `GET /api/briefing` `top_signals[0]`
- Ranked inbox: highest-severity signal wins consistently across surfaces.
- Bootstrap + degraded fixtures from existing test support modules.
- Required connector failures paired with `signal_runtime_summary_degraded`: connector
  signal wins on summary/briefing; summary-degraded placeholder excluded from counts.
- DashPro monitor families with the same cross-surface identity + actionable counts:
  Sentry / PostHog critical + transport/threshold warning, and Supabase Storage quota
  critical (≥90%) plus threshold warning (≥80% → severity `high`).
- DashPro monitor criticals (Sentry unresolved issues, PostHog auth/access failures)
  agree on identity fields and severity across inbox, summary, and briefing.

### Acceptable v1 degradation

- Dev/bootstrap signal set only (not full axon-local signal breadth).
- No live watch E2E in default gate (mocked inbox fetch).

## Gate

```bash
npm run verify:parity-a4
```

Slice gates also run the P-A4 modules so connector/monitor work cannot regress
cross-surface agreement without hitting the focused gate:

- `npm run verify:test3` / `npm run verify:connector-parity` — connector slice
- `npm run verify:dashpro-monitors` — DashPro monitor slice

Completes **Phase A — Run-state trust**.
