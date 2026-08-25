# Lead retry report — MoveIT

| Field | Value |
|---|---|
| Retry run | `run_0d68a13b1896` |
| Failed run retried | `run_eb27cfd30ee4` |
| Prior same failure | `run_ca22fab42bbd` |
| Failed task | `task-5b97d3a5c8bb47ee` (API now `404`) |
| Role | Lead (Jabulani) |
| Date | 2026-08-25 |

## What failed last time

Continuous worker completed file work, completion-gate preflight passed, then publish failed:

> Workspace delivery blocked: workspace delivery is not configured for MoveIT, so 3 changed path(s) cannot be published

Changed paths from gate receipt:

1. `docs/ops/retry-report.md`
2. `docs/ops/service-connections.md`
3. `docs/ops/workspace-baseline.md`

Isolation checkout was preserved then cleaned up; content was not recoverable from `/tmp`.

Acceptance checks on the failed run also reported `test` and `diff_budget` failures (mode=contract) before delivery block.

## What this retry changed

Rewrote the three blocked ops docs into the live project root write scope, plus a priorities plan:

| Path | Purpose |
|---|---|
| `docs/ops/workspace-baseline.md` | Binding, team, disk shape, product direction |
| `docs/ops/service-connections.md` | Control-plane / delivery posture |
| `docs/ops/retry-report.md` | This receipt |
| `plans/priorities-2026-08-25.md` | Bounded priority order |

## Verified facts used

- Control-plane run history for `run_eb27cfd30ee4` / `run_ca22fab42bbd`
- `GET /api/workspaces/MoveIT/company`
- On-disk inventory of the MoveIT project root (no `.git`; empty scaffolds)

## Still blocked

Workspace delivery remains unconfigured. Continuous-worker publish will fail again until Mira/Axon-X configures delivery for MoveIT (or an operator gate enables an equivalent publish path). Remy is still `waiting_approval` on the prior lead failure decision.

## Next step (filed)

Handoff to Mira (`workspace_axon_watch`) created and routed:

| Receipt | Id |
|---|---|
| Handoff | `handoff-c7c62d409f8f41cc` |
| Target task | `task-d5094a05110d4a9f` |
| Routed role | lead (Mira) |
| Status | routed |

Goal on that task: configure MoveIT workspace delivery so continuous runs can publish changed paths without the delivery-not-configured failure.
