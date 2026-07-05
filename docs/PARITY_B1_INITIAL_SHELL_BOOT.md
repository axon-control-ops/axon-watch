# P-B1 — Initial Shell Boot Expectations

## Parity row

`initial_shell_boot_expectations` in `config/parity-snapshot.json`

## Verification method (from ledger)

Measured boot checklist: settings/workspaces/runtime summary/shell render order.

## v1 scope

### In scope

- Default `npm run verify` passes `shell_boot_readiness` using
  `scripts/verify/fixtures/shell-boot-report.dev.json` (bootstrap-critical-path
  proxy under nightly threshold).
- `scripts/dev/measure_shell_boot.py` produces a report shape consumable by
  `scripts/verify/check_latency_budget.py`.
- Fitness budget no longer **PENDING** in default verify.

### Acceptable v1 degradation

- CI uses bootstrap-critical-path fixture, not Playwright browser automation.
- Nightly `./scripts/dev/verify-with-evidence.sh` may collect live browser samples.

### Out of scope

- Full Playwright shell paint measurement in default CI
- Desktop packaging startup contract

## Gate

```bash
npm run verify:parity-b1
```

## Promotion

On gate pass, update:

- `config/parity-snapshot.json` → `initial_shell_boot_expectations.status = verified`
- `docs/planning/PARITY_LEDGER.md` snapshot table
- `config/parity-closure-order.json` → `P-B1.status = done`

Next slice: **P-B2** (`runtime_summary_behavior` latency).
