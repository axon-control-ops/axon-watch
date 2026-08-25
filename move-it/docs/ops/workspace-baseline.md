# MoveIT workspace baseline

Captured: 2026-08-25 (retry of failed lead run `run_eb27cfd30ee4`)  
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
| Git repo in root | **no** (`.git` absent) |
| Certification (`project.axon.yaml`) | `inspect_only` |
| Stack | node |

## Team (company API)

| Name | Role | Status | Notes |
|---|---|---|---|
| Jabulani | Lead | executing (this retry) | last_outcome failed on delivery; last_run `run_eb27cfd30ee4` |
| Remy | Watcher | waiting_approval | pending decision about lead delivery failure |
| Ayesha | Frontend | idle | — |
| Reed | Backend | idle | — |
| Sol | Integrations | idle | last completed `run_8eae7646e5fb` |

## On-disk shape (verified)

Present files: `README.md`, `notes.txt`, `project.axon.yaml`.

Empty scaffold dirs: `docs/`, `output/`, `plans/`, `deploy/`, `infra/`, `.github/`, `tests/`, `__tests__/`, `node_modules/`.

Unusual scaffold: `package.json` and `package-lock.json` exist as **empty directories**, not package manifests. No app/source tree under allowed_paths such as `apps/`, `src/`, `lib/`, `services/` yet.

## Product direction (bounded)

1. Keep MoveIT as a company workspace with a thin, receipt-backed ops surface first.
2. Unblock continuous-worker publish (delivery) before fan-out implementation work can land.
3. After delivery works, let specialists own real trees: Ayesha (UI), Reed (API), Sol (connectors), Remy (signals/health).

## Open blocker

Workspace delivery is **not configured** for MoveIT. Continuous lead runs that change files fail at publish even when the completion gate preflight passes.
