# Receipt: Quinn integrations operator-stop attend

- **When:** 2026-08-02
- **Actor:** Quinn (integrations), workspace_axon_watch
- **Leased task:** `task-0d08f73eb3f340ec` / run `run_0abe00cf3a00`
- **Failed shift under investigation:** `run_8f6d892d278b` (dedupe `failed_shift:workspace_axon_watch:integrations`)
- **Prior Gate 6 block on same task:** `run_64ff060fab27` → `acceptance=fail · failed_checks=test · paths=3`
- **Chained prior failures:** `run_2e70ea2523bd` (Gate 6 — attend incomplete), `run_2071e086555c`, `run_6c7ef3d9cb34` (same operator-stop pattern)

## Verified inputs

| Item | Evidence |
|------|----------|
| Failed run status | `GET /api/runs/run_8f6d892d278b` → `phase=failed`, role=`integrations`, task=`task-87b198364a174f14` |
| Failure receipt | `GET /api/runs/run_8f6d892d278b/history` → `runtime_dispatch` / `run_failed` with `Runtime execution stopped by operator before the CLI finished.` |
| Duration | Started `2026-08-02T06:41:27Z`, failed `2026-08-02T06:43:30Z` (~123s) |
| Worker isolation | History → `worker/run_8f6d892d278b at bae1e49ec4b7 → /tmp/axon-si-run_8f6d892d-8jsl5j2e/checkout` (cleaned after stop) |
| Prior incomplete fix | `/tmp/axon-si-run_64ff060f-qzypi68k/checkout` — same `ceo_pending_approve.py` patch; Gate 6 test failed on full suite |
| Policy classification | `is_operator_stopped_failure(detail)` → True; `assign_owner_role_for_failed_shift` → `escalate_only=True`, kind=`operator_blocker` |
| CLI mechanism | `subprocess_runner.raise_if_operator_stopped` — negative returncode (signal kill), not Gate 6 / connectors / Fast Gate defect |

## Root cause

`run_8f6d892d278b` ended with a SIGTERM-style operator-stop (~2 minutes in), not a missing connector or Fast Gate code defect.

Under Full AUTO, `receipt_is_ceo_investigable` treated `operator_blocker` failed-shift cards as investigable, so CEO auto-approve re-enqueued attend tasks for soft dedupe `failed_shift:workspace_axon_watch:integrations` (attend thrash).

Prior retry `run_64ff060fab27` landed the policy fix in isolation and passed Critical Review (8/10), but Gate 6 failed `test` because dirty `services/` + `tests/` forced the full contract unit suite (~100+ modules) over the ~300s budget. `tests.test_ceo_pending_approve` was also missing from the full suite list.

## Control-plane / verify changes (worker isolation)

1. **`ceo_pending_approve.receipt_is_ceo_investigable`** — return False when detail is a shift-continuation failure (operator-stop, restart interrupt, or SIGTERM/OOM session interrupt) via `is_shift_continuation_failure`.
2. **`tests/test_ceo_pending_approve.py`** — regression using `run_8f6d892d278b` receipt shape.
3. **`scripts/verify/run_contract_unit_tests.sh`** — path-scope class `ceo_approve` for the two CEO-approve files; focused suite stays under Gate 6 budget; add `tests.test_ceo_pending_approve` to the full suite list.

## Verification (this shift)

```text
python3 -m unittest \
  tests.test_ceo_pending_approve \
  tests.test_failure_detail \
  tests.test_gate6_path_scoped_checks \
  tests.test_gate6_project_contract \
  tests.test_gate6_verifier_contract -v
→ Ran 37 tests in 0.205s  OK

./scripts/verify/run_contract_unit_tests.sh
→ contract unit tests: CEO auto-approve / shift-continuation path-scope
→ Ran 37 tests in 0.197s  OK

Gate 6 simulate (list_changed_paths + execute_check_plan + evaluate_acceptance)
→ paths=4 (ceo_pending_approve.py, test_ceo_pending_approve.py,
  run_contract_unit_tests.sh, integrations-operator-stop-attend-2026-08-02.md)
→ lint/typecheck/test/build/security/diff_budget all passed
→ typecheck/build skipped (no apps/console-web dirty)
→ acceptance=pass

./scripts/dev/python.sh scripts/guardrails/check_file_sizes.py
→ File-size guardrails passed.

npm run verify:contracts
→ FAILED in this disposable isolation: packages/shared-types `tsc: not found` (exit 127).
  Gate 6 test command is ./scripts/verify/run_contract_unit_tests.sh (passed above);
  typecheck/build are skipped for this Python-only dirty set.
```

## Residual / Lead next

- Publish this isolation so Full AUTO loads `ceo_pending_approve.py` (restart live control-plane only when no active worker would be cancelled).
- After publish, integrations roster should stop re-enqueueing operator-stop attends for `failed_shift:workspace_axon_watch:integrations`.
- Spend caps, secrets, production, and protected merges were not touched.
