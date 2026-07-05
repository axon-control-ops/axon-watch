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

### Acceptable v1 degradation

- Dev/bootstrap signal set only (not full axon-local signal breadth).
- No live watch E2E in default gate (mocked inbox fetch).

## Gate

```bash
npm run verify:parity-a4
```

Completes **Phase A — Run-state trust**.
