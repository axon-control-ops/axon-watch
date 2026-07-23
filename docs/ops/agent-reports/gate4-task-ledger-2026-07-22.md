# Gate 4 — Durable task ledger evidence

**Date:** 2026-07-22  
**Plan:** `docs/AXON-X-AUTONOMY-MASTER-PLAN.md` Gate 4  
**Depends on:** Gate 3 (`11e3bce`); Gate 2 residuals (`0052350`)  
**Scheduler:** remains **off** by default

---

## What shipped

### Ledger + APIs

- SQLite `workspace_tasks` via `services/control-plane/app/persistence/task_store.py`
- Fields: goal, acceptance, risk, owner_role, dependencies, lease, attempt budget, terminal outcome, run_id
- HTTP: create/list/get/lease/renew-lease/complete/fail/cancel (`routes/tasks.py`)
- `runs.task_id` column; continuous `create_run(..., require_leased_task=True)` binds leased tasks

### Continuous worker enforcement

- Scheduler claims an open task for the role before starting a run
- Dispatch refuses without a leased `task_id`; renews lease at start; completes/fails ledger on outcome
- Worker prompt is task-scoped (no free-form self-selected continuous work)
- Dependencies must be `completed` before lease
- Attempt budgets + lease contention enforced in store

### Mission Control surface

- Task board panel + shell slice + `tasks-api.ts`
- Mounted on operator Mission Control grid (`OperatorTaskBoardPanel`)

### Related operator UX (same landing)

- Concurrent IDE conversation streams (per-thread SSE; tab switch does not tear down other runs)
- Brain galaxy: label every named workspace; muted stable workspace hues

---

## Test proof

```text
python -m unittest tests.test_gate4_task_ledger tests.test_workspace_agent_scheduler -q
npx vitest run src/lib/operator-task-board-view.test.ts src/features/brain-galaxy/galaxy-node-label-policy.test.ts
```

---

## Exit checklist

| Criterion | Status |
| --- | --- |
| Every continuous worker run from one leased task | **Met** |
| No continuous shift without task ID | **Met** |
| Attempt budgets + leases enforced | **Met** (renew on dispatch; deps gated) |
| Task board visible | **Met** (Mission Control Grid) |
| Scheduler re-enabled by default | **No** — intentionally off |
| Interactive IDE employee runs without task | Still allowed unless `require_leased_task=True` (continuous path always sets it) |

**Gate 4 result:** **CLOSED** for durable leased continuous work. Next: Gate 5 Lead planner + fan-out.
