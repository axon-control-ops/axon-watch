# Receipt: DashPro Attend + Product Fees control-plane fix

- **When:** 2026-07-31
- **Actor:** Rowan (watcher), workspace_axon_watch
- **Leased task:** `task-018c07344f1b4393` / run `run_937e3ae49cd7`
- **Handoff:** `handoff-52c564e087624689` (DashPro → Axon-X, routed watcher)

## Verified inputs

| Item | Evidence |
|------|----------|
| Attend task open+approved | `GET /api/tasks/task-809465afd26b4e23` → status=`open`, risk=`approved`, approval=`auton-e9a1828171964fa1`, attempts `0/1` |
| Priya usage failure | `GET /api/runs/run_a5b07cfc902d/history` → receipt `runtime_dispatch` with `ActionRequiredError` / out of usage |
| Product Fees exhausted | `GET /api/tasks/task-56605bdd03ea492e` → status=`failed`, attempts `3/3` |
| Duplicate attend cancelled | task-9ead218dfa214894 already cancelled (per lease goal) |

## Control-plane changes

1. **`POST /api/tasks/{task_id}/reopen`** — reopen/re-budget a failed ledger task (`attempt_budget`, `reset_attempts`).
2. **Usage-limit attempt refund** — worker finalize calls `fail_task(..., refund_attempt=True)` when the run detail is a Cursor out-of-usage failure, so the last attempt slot is not burned.
3. **Operator Start gate** — Start refuses when `usage_limit_blocks_auto_start` is true (same skip policy as continuous workers).

## Live follow-through (this shift)

- Restarted `control-plane.service` after syncing the reopen/refund/Start-gate code into the live tree.
- `POST /api/tasks/task-56605bdd03ea492e/reopen` → **200**, status=`open`, attempts **0/3** (no DashPro app code changes).
- Attend `task-809465afd26b4e23` left **open + approved**, attempts **0/1**, approval `auton-e9a1828171964fa1` (not leased).
- Board receipt task on Axon-X: `task-46740b31f69149f0` → **completed** (terminal outcome cites handoff-52c564e087624689 / run_937e3ae49cd7).
- Unit tests: `python3 -m unittest tests.test_gate4_task_ledger tests.test_operator_start_task -v` → **OK** (22 tests).
