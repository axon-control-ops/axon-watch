# MoveIT workspace baseline

Captured: 2026-08-26 (retry of failed lead run `run_5f7fd88f9487`; live run `run_6c72a01d1632`)
Owner: Jabulani (Lead)
Source of truth for this note: live control-plane API + on-disk project root inspection

## Binding

| Field | Value |
|---|---|
| Workspace id | `MoveIT` |
| Display name | move-it |
| Connection | project_path |
| Project root | `/run/media/vaxon/axon-data/repos/axon-nvme/repos/axon-watch/move-it` |
| Auto-enabled | true |
| Active team | true |
| Git repo in root | not verified this turn via shell (absolute `.git` probe blocked); prior receipts reported absent |
| Certification (`project.axon.yaml`) | `build` |
| Stack | node |

## Team (company API, this turn)

| Name | Role | Status | Notes |
|---|---|---|---|
| Jabulani | Lead | executing | failed `run_5f7fd88f9487`; active retry `run_6c72a01d1632` |
| Remy | Watcher | waiting_approval | decision on lead failure; last fail Gate 6 evidence |
| Ayesha | Frontend | idle | — |
| Reed | Backend | idle | last fail Gate 6 evidence |
| Sol | Integrations | idle | last fail Gate 6 evidence |

## On-disk shape (verified this turn)

| Item | Status |
|---|---|
| `package.json` | **file** present (403 bytes; `name=move-it`, `npm test` → `node --test tests/smoke.test.js`) |
| `package-lock.json` | **file** present (lockfileVersion 3) |
| `tests/smoke.test.js` | present |
| Ops docs | under `docs/ops/` |
| App/source trees | still absent (`apps/`, `src/`, `services/` not in inventory) |

Terminal receipt: `agent-job-8c4b12008fde` (exit 0).

## Product direction (bounded)

1. Keep MoveIT as a company workspace with a receipt-backed ops surface first.
2. Unblock continuous-worker publish (delivery) before fan-out implementation work can land.
3. Node manifests are no longer empty directories — next product slice is schema/API (Reed) + thin shell (Ayesha), only after delivery works.
4. Do not invent specialist starts without new task/run ids from the ledger.

## Open blockers (2026-08-26)

1. Workspace delivery **not configured** — continuous publish fails with the same error as `run_5f7fd88f9487`.
2. Cross-workspace handoff create from this runtime needs an **operator bearer token** (`auth_required=true`).
3. Remy’s waiting_approval decision still open on the lead failure.
4. No application code yet — smoke test only.

See `docs/ops/mvp-verification-plan.md` and `docs/ops/service-connections.md`.
