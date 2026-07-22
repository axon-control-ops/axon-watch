# Gate 5 — Lead planner and conflict policy (2026-07-22)

## Scope

- Persist `LeadTaskPlan` → `workspace_tasks` (`lead_task_persist`)
- Materialize fan-out → leased tasks + ready specialist runs (`lead_fan_out`)
- Persist Lead plans, task mappings, replan receipts, and synthesis receipts
- Cancel obsolete open/leased tasks on explicit replan
- Enforce exclusive-path conflicts both inside one DAG and across leased plans
- Synthesize terminal specialist outcomes after all plan tasks finish
- HTTP: `POST /api/workspaces/{id}/lead/plan`, `.../lead/fan-out`,
  `.../lead/replan`, and `/api/lead/plans/{id}/synthesize`
- Specialty route returns `reason=lead_fan_out` (no single winner)
- KAIRO handoff can emit `type=lead_fan_out` with task/run receipts

## Deliberately bounded

- Auto Lane B dispatch / enabling continuous scheduler
- Model-authored prose synthesis (the current synthesis is deterministic and receipt-backed)
- Automatically opening every specialist tab in the console

## Proof

```bash
./scripts/dev/python.sh -m unittest \
  tests.test_lead_task_plan \
  tests.test_lead_fan_out \
  tests.test_lead_replan -q
npm test -w @axon-watch/console-web -- --run src/lib/workspace-stream-ui.test.ts
```

Exit criteria:

| Criterion | Status |
| --- | --- |
| One goal → ordered task plan | **Met** |
| Roles assigned from company roster | **Met** |
| Overlapping edits cannot run concurrently | **Met** — DAG deps + lease-time path conflict |
| Obsolete tasks cancelled on replan | **Met** — explicit `/lead/replan` |
| Replans receipt-backed | **Met** — durable `lead_plan_receipts` |
| Check with all → N specialist runs/tasks | **Met** — materialize + run receipts |
| Lead synthesizes terminal specialist outcomes | **Met** — deterministic receipt-backed synthesis |
| Switching IDE tabs preserves sibling streams | **Met** — per-thread stream state + tab-focus proof |

## Evidence artifacts

- Sample goal → DAG:
  `docs/ops/agent-reports/gate5-sample-task-dag-2026-07-22.json`
- Planner/fan-out/replan tests:
  `tests/test_lead_task_plan.py`, `tests/test_lead_fan_out.py`,
  `tests/test_lead_replan.py`
- Tab-switch state proof:
  `apps/console-web/src/lib/workspace-stream-ui.test.ts`

## Result

Scheduler remains **off**. Fan-out creates runs; operators or a later Gate 5/10
slice start Lane B work intentionally.

**Gate 5 CLOSED. Gate 6 (mandatory verifier contract) is unlocked.**
