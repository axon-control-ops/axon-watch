# P-A1 — Run Stop / Resume Cross-Surface Parity

## Parity row

`run_stop_resume` in `config/parity-snapshot.json`

## Verification method (from ledger)

End-to-end run flow with stop and resume receipts; UI verifies same state in
dock and runtime strip.

## v1 scope

### In scope

- After **stop**: `/api/runs/{id}`, `/api/runs` list entry, and
  `/api/runtime/summary` `active_runs[0]` agree on `phase`, `status`, and
  capability flags (`can_stop`, `can_resume`).
- Run history includes `operator_stop` receipt before resume.
- After **resume**: same surfaces agree on `executing` / `running` with
  `operator_resume` receipt appended.
- Mission control projection (`operator-status-radar-view`) reflects paused and
  executing phases from the same run DTO the shell store loads after
  `refreshRunSurfaces()`.

### Acceptable v1 degradation

- Browser click E2E (Playwright) deferred to nightly shell-boot harness; proof uses
  API cross-surface consistency + UI projection unit tests.
- Resume affordance may remain mission-control primary; Attention stop button
  already wired.

### Out of scope

- Full agent transcript streaming in center feed
- Stop/resume from every legacy axon-local surface

## Gate

```bash
npm run verify:parity-a1
```

## Promotion

On gate pass, update:

- `config/parity-snapshot.json` → `run_stop_resume.status = verified`
- `docs/planning/PARITY_LEDGER.md` snapshot table
- `config/parity-closure-order.json` → `P-A1.status = done`

Next slice: **P-A2** (`approval_boundaries`).
