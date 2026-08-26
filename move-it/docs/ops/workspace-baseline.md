# MoveIT workspace baseline

Captured: 2026-08-26 (Lead retry `run_3fd4b12aed22`)
Owner: Jabulani (Lead)
Source: live control-plane API + on-disk project root inspection

## Binding

| Field | Value |
|---|---|
| Workspace id | `MoveIT` |
| Display name | move-it |
| Connection | project_path |
| Project root | `/run/media/vaxon/axon-data/repos/axon-nvme/repos/axon-watch/move-it` |
| Auto-enabled | true |
| Active team | true |
| Certification (`project.axon.yaml`) | `build` |
| Stack | node |

## Team (company API, this turn)

| Name | Role | Status | Notes |
|---|---|---|---|
| Jabulani | Lead | executing | retry `run_3fd4b12aed22` |
| Remy | Watcher | watching | last completed `run_4d4642fb01ff`; pipeline blocked on probe file (cleared this retry) |
| Ayesha | Frontend | executing | active `run_8d202dcc94de`; Gate 6 confidence miss |
| Reed | Backend | executing | active `run_a7cb06d07985`; contracts promoted; 16/16 tests |
| Sol | Integrations | executing | active `run_b5d82a6fc8a3`; delivery endpoint now configured; Sentry org/project still pending |

## On-disk shape (verified this turn)

| Item | Status |
|---|---|
| `package.json` | present — `npm test` → `node --test tests/*.test.js` |
| `services/api/` | **present** — customer-home, job-confirmation, shared |
| `tests/` | contract + schema + smoke tests; **16/16 pass** |
| `apps/customer/src/` | Expo screens + components promoted |
| `output/contract-work/` | staging mirror (canonical paths now primary) |
| Ops docs | under `docs/ops/` |

Terminal receipt: `agent-job-6742604d6d89` (exit 0, 16 pass / 0 fail).

## Product direction (bounded)

1. First slice (Customer Home + Job Confirmation + Reed contracts) is **promoted and test-green**.
2. Keep **P0-1 workspace delivery** verified before continuous publish lands further work.
3. Remy signs Layer A automated verify, then B/C manual C1–C3 with Ayesha.
4. Do not fan out Driver/Ops screens until C1–C3 are signed.

## Open blockers (2026-08-26)

1. Historical Mira handoff `handoff-fb7fd86e7d8f41e8` failed before the delivery endpoint repair; review or retry through the operator workflow.
2. Ayesha Gate 6 confidence clause on frontend retry.
3. Remy manual journey sign-off pending.

See `plans/priorities-2026-08-26.md` and `docs/ops/mvp-verification-plan.md`.
