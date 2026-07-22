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
- Approved-backlog / goal-id ingestion (planner still takes a raw goal string)
- Creating IDE chat threads for each specialist (materialize creates leased tasks + runs)

## Proof

```bash
./scripts/dev/python.sh -m unittest \
  tests.test_lead_task_plan \
  tests.test_lead_fan_out \
  tests.test_lead_replan -q
```

Master-plan exit criteria:

| Criterion | Status |
| --- | --- |
| One goal → ordered task plan | **Met** |
| Roles assigned from company roster | **Met** |
| Overlapping edits cannot run concurrently | **Met** — DAG deps + lease-time path conflict |
| Obsolete tasks cancelled on replan | **Met** — explicit `/lead/replan` |
| Replans receipt-backed | **Met** — durable `lead_plan_receipts` |
| Check with all → N specialist runs/tasks | **Met** — materialize + run receipts |
| Lead synthesizes terminal specialist outcomes | **Partial** — deterministic terminal-status receipt, not model prose |

Related UX (Gate 4 infrastructure; not a Gate 5 exit criterion):

| Item | Status |
| --- | --- |
| Per-thread stream UI state helpers | Covered by `workspace-stream-ui.test.ts` |
| `selectIdeThread` leaves sibling SSE connected | Implemented in `shell.ts` (Gate 4); **no automated EventSource assertion in Gate 5** |

## Evidence artifacts

- Sample goal → DAG:
  `docs/ops/agent-reports/gate5-sample-task-dag-2026-07-22.json`
- Planner/fan-out/replan tests:
  `tests/test_lead_task_plan.py`, `tests/test_lead_fan_out.py`,
  `tests/test_lead_replan.py`
- Stream-UI helper coverage (not SSE lifecycle):
  `apps/console-web/src/lib/workspace-stream-ui.test.ts`

## Result

Scheduler remains **off**. Fan-out creates runs; operators or a later Gate 5/10
slice start Lane B work intentionally.

**Gate 5 CLOSED against master-plan exit criteria** (goal→DAG, role assignment,
path serialization, receipt-backed replan, multi-specialist fan-out). Gate 6
(mandatory verifier contract) is unlocked. Residual product gaps above remain
documented, not hidden.
