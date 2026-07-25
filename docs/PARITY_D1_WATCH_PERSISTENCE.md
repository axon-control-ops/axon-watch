# P-D1 — Watch SQLite Persistence

## Deliverable

SQLite persistence for axon-watch **commands**, **events**, and **delivery receipts**
replacing in-memory stores.

## v1 scope

### In scope

- `services/axon-watch/app/persistence/watch_store_sqlite.py` schema + connection
- `AXON_WATCH_WATCH_SERVICE_DB` env (default `./.local/state/axon-watch.sqlite3`)
- Bounded event/receipt retention (200 rows, same as prior in-memory cap)
- Restart-survival proof: data written before client close is readable after reconnect
- Existing TEST-4 / TEST-5 contract tests unchanged

### Acceptable v1 degradation

- Signals/inbox remain computed on read (not persisted)
- Single-node SQLite; no replication or migration playbook

### Out of scope

- Real delivery channel adapters (P-D2)
- Dedicated-host live smoke (P-D3)

## Gate

```bash
npm run verify:parity-d1
```

## Promotion

On gate pass, update `config/parity-closure-order.json` → `P-D1.status = done`,
`next_slice = P-D2`.
