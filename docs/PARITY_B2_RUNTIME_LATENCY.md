# P-B2 — Runtime Summary Latency Budgets

## Parity row

`runtime_summary_behavior` in `config/parity-snapshot.json` (latency evidence)

## Verification method (from ledger)

DTO contract tests + boot-path UI render using summary only; fitness budgets for
warm route timing.

## v1 scope

### In scope

- Default `npm run verify` passes `runtime_summary_latency` and
  `watch_summary_latency` using CI fixture sample files.
- `scripts/dev/collect-verify-evidence.sh` measures watch summary route
  (`/internal/watch/summary`), not health probe latency.
- Thresholds from `scripts/verify/verification_config.json` (300ms runtime,
  200ms watch p95).

### Acceptable v1 degradation

- CI uses checked-in sample fixtures, not live stack timing.
- Nightly evidence collection may replace fixtures when dev stack is up.

### Out of scope

- Per-region latency SLOs
- Cold-start measurement

## Gate

```bash
npm run verify:parity-b2
```

## Promotion

Contributes to `runtime_summary_behavior` verification together with **P-B3**.

Next slice: **P-B3** (boot-critical field allowlist).
