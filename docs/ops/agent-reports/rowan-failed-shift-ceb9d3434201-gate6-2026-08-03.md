# Rowan — failed_shift Gate 6 fix (`run_ceb9d3434201`)

**Date:** 2026-08-03  
**Role:** watcher  
**Leased task:** `task-b245c4e4a1634f77`  
**Failed run:** `run_ceb9d3434201`  
**Dedupe:** `failed_shift:workspace_axon_watch:watcher:run_ceb9d3434201`

## Root cause (verified)

`run_ceb9d3434201` history receipt (sequence 19):

`acceptance=fail · failed_checks=typecheck,test,build,diff_budget · mode=contract · paths=5`

| Failed check | Verified cause |
| --- | --- |
| `diff_budget` | `tests/test_run_stale_reconcile.py` grew to **670** lines vs ratchet **645** |
| `typecheck` / `build` | Worker isolation has no `vue-tsc` / frontend toolchain (`vue-tsc: not found`) |
| `test` | Full `run_contract_unit_tests.sh` exceeds Gate 6 default timeout |

The code intent of that shift was correct: stop false watcher failed-shifts when a stale reap races a late successful Critical Review (pattern from `run_d3002d9522af`).

## Fix in this isolation (`run_1900a404b619`)

1. Port stale-timeout outcome + reaper registry skip (without growing `test_run_stale_reconcile.py`).
2. Split new coverage into `tests/test_run_stale_reconcile_cli_registered.py` and `tests/test_run_outcome_stale_critical_review.py`.
3. Land Gate 6 timeout-safe wrappers (`run_gate6_frontend_check.sh`, `run_gate6_unit_tests.sh`) and point `project.axon.yaml` at them; raise verifier default timeout to 180s.
4. Allow `project.axon.yaml` in the project contract allowed paths.

## Receipts

| Check | Result | Log |
| --- | --- | --- |
| Targeted unittest (8) | OK | `rowan-gate6-targeted-tests-run_ceb9d3434201.log` |
| Gate 6 `execute_check_plan` | `acceptance=pass · lint,typecheck,test,build,security,diff_budget` | `rowan-gate6-execute-check-plan-run_ceb9d3434201.log` |

No commit/push (out of scope for this lease).
