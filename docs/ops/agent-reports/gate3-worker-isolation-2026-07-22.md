# Gate 3 — Per-task disposable checkout evidence

**Date:** 2026-07-22  
**Plan:** `docs/AXON-X-AUTONOMY-MASTER-PLAN.md` Gate 3  
**Baseline HEAD:** `feat/autonomous` at capture time (working-tree Gate 3 slice; not yet committed)  
**Depends on:** Gate 2 thin containment closed for unlocking Gate 3 engineering  
**Scheduler:** remains **off** (`effective_enabled: false` expected until Gate 4+)

---

## What shipped in this slice

### Named per-run worker branch + worktree

- `services/control-plane/app/safe_improvement/isolated_executor.py`
  - Replaces `git worktree add --detach` with `git worktree add -b worker/<run_id> <path> <baseline>`
  - Clone fallback pins the same named branch via `checkout -B`
  - Sidecar `baseline.json` records `worker_branch`
  - Uniquifies once (`worker/<run_id>-<hex>`) if the preferred branch already exists

### Cleanup receipts

- Worktree remove + prune on the bound live root
- `git branch -D <worker_branch>` after worktree removal
- Cleanup receipt fields: `worker_branch`, `branch_deleted`, `branch_cleanup_error`

### Path forbid (writes outside disposable root)

- `resolve_path_within_isolation` / `assert_mutation_within_isolation`
- Candidate apply / restore / promote paths go through the guard
- Rejects `../` escapes and absolute paths into the live bound root

### Worker isolation wrapper

- `worker_isolation.isolation_receipt_summary` includes `branch=`

---

## Test proof

```text
python -m unittest tests.test_gate3_worker_isolation -v
Ran 5 tests … OK

  - test_worker_isolation_is_not_live_checkout_and_cleans_up
  - test_named_worker_branch_created_and_deleted_on_cleanup
  - test_concurrent_isolations_leave_live_root_untouched
  - test_refuse_path_outside_disposable_root
  - test_refuse_missing_isolation_root

PYTHONPATH=services/control-plane python -m unittest tests.test_safe_improvement -q
Ran 8 tests … OK
```

Included in `npm run verify:contracts` via `scripts/verify/run_contract_unit_tests.sh` (`tests.test_gate3_worker_isolation`).

### Concurrent isolation / live-root `git status`

`test_concurrent_isolations_leave_live_root_untouched`:

1. Capture porcelain `git status` on the bound live root.
2. Create two isolations (`run_conc_a`, `run_conc_b`) with distinct trees.
3. Write different files into each disposable root only.
4. Assert live root still has neither file; porcelain status unchanged mid-flight.
5. Cleanup both; porcelain status still equals the before snapshot.

---

## Gate 3 exit checklist (honest)

| Criterion | Status |
| --- | --- |
| Two workers can change the same repository without sharing a working tree | **Met** (concurrent unit proof) |
| Operator checkout remains untouched by continuous workers | **Met** (status before/after + mutation only in disposable roots) |
| Failed / finished tasks leave cleanup receipts, not dirty shared folders | **Met** (cleanup receipt + branch delete) |
| Named `worker/<run_id>` branch per run | **Met** |
| Forbid writes outside disposable root | **Met** (path resolve guard; not a full OS sandbox) |
| Continuous scheduler re-enabled | **Not done** — intentionally remains off |

**Gate 3 result:** **CLOSED** for disposable per-run checkout / named branch / concurrent isolation proofs.  
Unlocks Gate 4 (durable task ledger). Does **not** re-enable the continuous scheduler.

---

## Residual / deferred (not this slice)

1. Gate 2 residuals: CSRF, rate limits, step-up Full Access, forced `local_token` on remote.
2. Gate 4+: task leases, Lead, verifier, PR/CI, staging, mobile.
3. Composer: prove agent consumes attached CSV/PDF contents.
4. Dirty agent/roster speech WIP parked in git stash (`wip: agent speech/roster park Gate3`) — restore separately; do not mix into Gate 3 commits.

---

## Next gate unlocked

**Gate 4 — Durable task ledger** (scheduler still off until leases exist).
