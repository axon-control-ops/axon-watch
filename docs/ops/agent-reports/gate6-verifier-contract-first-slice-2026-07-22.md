# Gate 6 — Mandatory verifier contract (first slice)

**Date:** 2026-07-22  
**Branch context:** `feat/autonomous` working tree  
**Scope:** fail-closed acceptance evidence for **leased worker runs** (`task_id` set)

## Implemented

- `services/control-plane/app/workspace_agents/verifier_contract.py`
  - `acceptance_evidence` receipts with pass/fail markers
  - `enforce_acceptance_for_publish(run_id)` for task-bound runs
- `mark_review_ready` and `complete_run` (from `executing`) call the enforce hook when `task_id` is present
- Operator thin-slice runs **without** `task_id` remain unchanged (preserves existing review-ready UX tests)
- Unit tests: `tests/test_gate6_verifier_contract.py` (5 cases) — missing/failed evidence blocks; passing evidence allows; operator path still works

## Not yet Gate 6 complete

- Auto-generate/run lint/type/test/build/security/diff-budget checks
- Immutable separate verifier role / agent
- Block PR creation (Gate 8 dependency)
- Force Lane B `finalize_lane_b_agent_run` to produce real check receipts before complete (today CRC confidence only)
- Sample production acceptance receipt from a live worker shift

## Exit criteria progress

| Criterion | Status |
| --- | --- |
| No **task-bound** run → review-ready without acceptance evidence | **Met** (unit-tested) |
| Failed acceptance blocks publishing surfaces | **Met** for review_ready + complete-from-executing |
| Diff policy rejects secrets / out-of-scope | **Not started** |
| Verifier contract tests / fail-closed examples | **Started** (`test_gate6_verifier_contract`) |

## Next Gate 6 slice

1. Record real check-command outputs into `acceptance_evidence` from worker finalize.
2. Apply the same enforce hook before Lane B `complete_run` even when CRC confidence is present (confidence ≠ acceptance).
3. Add diff-budget / secrets path policy helper consumed by `record_acceptance_evidence`.
