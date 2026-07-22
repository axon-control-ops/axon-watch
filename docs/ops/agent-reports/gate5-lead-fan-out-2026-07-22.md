# Gate 5 slice — Lead fan-out materialize (2026-07-22)

## Scope

- Persist `LeadTaskPlan` → `workspace_tasks` (`lead_task_persist`)
- Materialize fan-out → leased tasks + ready specialist runs (`lead_fan_out`)
- HTTP: `POST /api/workspaces/{id}/lead/plan`, `.../lead/fan-out`
- Specialty route returns `reason=lead_fan_out` (no single winner)
- KAIRO handoff can emit `type=lead_fan_out` with task/run receipts

## Not in this slice

- Auto Lane B dispatch / enabling continuous scheduler
- Lead synthesis of specialist results after all runs complete
- Console UI multi-tab open-all for fan-out

## Proof

```bash
./scripts/dev/python.sh -m unittest tests.test_lead_task_plan tests.test_lead_fan_out -q
```

Exit criteria progress:

| Criterion | Status |
| --- | --- |
| One goal → ordered task plan | yes (slice 1) |
| Overlapping edits cannot run concurrently | yes (deps + deferred runs) |
| Replans receipt-backed | partial (materialize receipt; cancel-obsolete still open) |
| Check with all → N specialist runs/tasks | yes (materialize + receipts) |

## Residual

Scheduler remains **off**. Fan-out creates runs; operators or a later Gate 5/10
slice start Lane B work intentionally.
