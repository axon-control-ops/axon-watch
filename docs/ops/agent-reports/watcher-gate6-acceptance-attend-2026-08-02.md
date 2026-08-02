# Receipt: Rowan watcher Gate 6 acceptance attend

- **When:** 2026-08-02
- **Actor:** Rowan (watcher), workspace_axon_watch
- **Leased task:** `task-c638c3afcd86499e` / run `run_8c4662dd2565`
- **Failed shift under investigation:** `run_15eba4039484` (dedupe `failed_shift:workspace_axon_watch:watcher`)
- **Prior task on that run:** `task-290c74c366b74f97` (operator-stop CEO gate fix; Gate 6 test timeout)

## Verified inputs

| Item | Evidence |
|------|----------|
| Failed run status | `GET http://127.0.0.1:8787/api/runs/run_15eba4039484` → `phase=failed`, role=`watcher` |
| Delivery block | `current_step`: `Workspace delivery blocked: missing or failing acceptance_evidence (Gate 6)` |
| Acceptance receipt | history `acceptance_evidence`: `acceptance=fail · failed_checks=test · mode=contract · paths=3` |
| Dirty paths (isolation) | `ceo_pending_approve.py`, `test_ceo_pending_approve.py`, receipt doc |
| Root cause (test) | Small control-plane fix triggered **full** `run_contract_unit_tests.sh` (~133 modules) → exceeded Gate 6 300s test budget |
| Underlying product fix | Operator-stopped watcher shifts (`run_66a7b613f08a`) were still CEO-investigable → attend churn loop |

## Fix (this shift, disposable isolation)

1. **`ceo_pending_approve.py`** — exclude `is_shift_continuation_failure(detail)` from `receipt_is_ceo_investigable` (operator stop / SIGTERM / restart → escalate only).
2. **`tests/test_ceo_pending_approve.py`** — regression test for Rowan operator-stop receipt on `run_66a7b613f08a`.
3. **`run_contract_unit_tests.sh`** — **narrow** path-scope: when dirty code is ≤8 files under `services/control-plane/` and/or `tests/test_*.py`, run derived unittest modules only (not the full suite).

No secrets, production, protected merges, or spend caps were touched.

## Verification (this shift)

```text
PYTHONPATH=services/control-plane python3 -m unittest tests.test_ceo_pending_approve tests.test_failure_detail -v
→ Ran 17 tests in 0.091s  OK
```

```text
./scripts/verify/run_contract_unit_tests.sh
→ contract unit tests: narrow path-scope (1 module(s))
→ tests.test_ceo_pending_approve — Ran 5 tests  OK
```

```text
Gate 6 simulation (load_repo_contract + execute_check_plan + evaluate_acceptance)
→ changed_paths=4 (ceo_pending_approve + test + run_contract_unit_tests.sh + receipt doc)
→ acceptance=pass · lint,typecheck,test,build,security,diff_budget (passed=True, ~22s)
```

```text
python3 scripts/guardrails/check_file_sizes.py
→ File-size guardrails passed.
```

```text
GET /health + /api/runtime/summary
→ control-plane ready, watch connected
```

Spend caps, secrets, production, protected merges, and production were not touched.

## Lead next

- Restart control-plane when safe so live CEO gate + narrow test scope apply on finalize.
- Watcher should stop re-enqueueing operator-stop attends for `failed_shift:workspace_axon_watch:watcher`.
