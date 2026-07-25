# P-B3 — Runtime Summary Boot-Critical Fields

## Parity row

`runtime_summary_behavior` in `config/parity-snapshot.json` (field allowlist)

## Verification method (from ledger)

DTO contract tests + boot-path UI render using summary only; boot-critical
identity and degraded state must remain correct.

## v1 scope

### In scope

- `config/runtime-summary-boot-critical-fields.json` allowlist documents fields
  the console boot path depends on.
- `scripts/verify/check_runtime_summary_boot_fields.py` validates contract
  fixture and live assembler output.
- `/api/runtime/summary` response includes all allowlisted fields (integration
  test with mocked watch probes).

### Acceptable v1 degradation

- Fewer optional enrichment fields than axon-local runtime truth surfaces.
- Allowlist covers boot-critical subset only, not full axon-local parity.

### Out of scope

- Field-by-field semantic parity with every axon-local runtime panel
- Historical runtime telemetry fields

## Gate

```bash
npm run verify:parity-b3
```

## Promotion

On gate pass (with P-B2), update:

- `config/parity-snapshot.json` → `runtime_summary_behavior.status = verified`
- `docs/planning/PARITY_LEDGER.md` snapshot table
- `config/parity-closure-order.json` → `P-B3.status = done`

Next slice: **P-C1** (`kairo_persona_operator_copy`).
