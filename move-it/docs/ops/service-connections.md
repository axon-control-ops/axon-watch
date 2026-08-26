# MoveIT service-connection posture

Captured: 2026-08-26 (retry of failed lead run `run_5f7fd88f9487`; live run `run_6c72a01d1632`)
Owner: Jabulani (Lead)
Verified against: control-plane `GET /api/workspaces/MoveIT*`, company roster, run history

## Control plane

| Item | Status |
|---|---|
| Control plane base | reachable at `http://127.0.0.1:8787` |
| Workspace record | present (`MoveIT`, `connection_kind=project_path`) |
| Company roster | 5 employees loaded |
| Open tasks queue | empty (`GET .../tasks` → `items: []`) |
| Open handoffs | empty (`GET .../handoffs` → `count: 0`) |
| Failed lead run | `run_5f7fd88f9487` — status `error`, task `task-be593ba8fe4442d0` |
| Active lead run | `run_6c72a01d1632` — this retry |

## Service connection (live)

| Item | Status |
|---|---|
| configured | **true** |
| ready | **true** |
| operator `.env` | **absent** at project root |
| hint | Live service bridge ready from unlocked vault; operator `.env` optional |
| services_resolved | github / sentry / supabase → **true** |
| env keys from vault | `GH_TOKEN`, `SENTRY_AUTH_TOKEN`, `SUPABASE_ACCESS_TOKEN` present; several URL/org/project keys still missing |

## Delivery / publish

| Item | Status |
|---|---|
| Workspace delivery config | **missing** — publish blocked |
| Evidence | `run_5f7fd88f9487` failed with: workspace delivery is not configured for MoveIT, so 6 changed path(s) cannot be published |
| Isolation checkout | `/tmp/axon-si-run_5f7fd88f-o916t63f/checkout` — cleaned up before this retry |
| `GET .../delivery` | `404 Not Found` |
| Sandbox | off (`enabled=false`) |
| Mutating handoff API | requires `Authorization: Bearer <operator token>` |

## Project contract (`project.axon.yaml`)

- `certification_level`: `build`
- `allowed_paths` include `docs/`, `output/`, `scripts/`, `config/`, app/service trees, and `README.md`
- Verifier requires `test`
- Forbidden: `.env`, `.env.local`, `secrets/**`

## Prior Axon-X handoffs (stale; not recreated this turn)

| Handoff | Status | Notes |
|---|---|---|
| `handoff-c7c62d409f8f41cc` | failed | target task `404` |
| `handoff-685af9e940944325` | failed | 2026-08-25 |

New Mira handoff **not created** this turn — POST blocked by missing operator bearer token.

## Needed next connection (not owned here)

Axon console / control-plane delivery binding for MoveIT must be configured so continuous workers can publish into the real project root. Owned by Axon-X (Mira). Sir King must either supply an operator token for handoff POST, enable delivery in the console, or ask VAXON to triage the host delivery policy.
