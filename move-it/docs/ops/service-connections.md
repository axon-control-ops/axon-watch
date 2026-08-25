# MoveIT service-connection posture

Captured: 2026-08-25 (retry of failed lead run `run_eb27cfd30ee4`)  
Owner: Jabulani (Lead)  
Verified against: control-plane `GET /api/workspaces/MoveIT`, company roster, run history

## Control plane

| Item | Status |
|---|---|
| Control plane base | reachable at configured local control-plane port |
| Workspace record | present (`MoveIT`) |
| Company roster | 5 employees loaded |
| Open tasks queue | empty (`GET .../tasks` → `items: []`) |
| Failed lead task | `task-5b97d3a5c8bb47ee` no longer retrievable (`404`) |

## Delivery / publish

| Item | Status |
|---|---|
| Workspace delivery config | **missing** — publish blocked |
| Evidence | `run_ca22fab42bbd` and `run_eb27cfd30ee4` both failed with: workspace delivery is not configured for MoveIT, so 3 changed path(s) cannot be published |
| Isolation checkouts | cleaned up (`/tmp/axon-si-run_eb27cfd3-5g8898yb/checkout` and `...ca22...` absent) |
| Sandbox publish API | route exists (`POST /api/workspaces/{id}/sandbox/publish`) — not a substitute for configured workspace delivery on continuous workers |
| Git remote delivery | blocked by missing `.git` in project root |

## Project contract (`project.axon.yaml`)

- `allowed_paths` include `docs/`, `output/`, `scripts/`, `config/`, app/service trees, and `README.md`.
- Verifier requires `test`.
- Forbidden: `.env`, `.env.local`, `secrets/**`.

## Related completed specialist work

- Sol (Integrations) completed `run_8eae7646e5fb` and earlier retry `run_b6476afcdbef`.
- Those runs did not leave documented changed_files on the completion-gate receipts inspected for this retry.

## Needed next connection (not owned here)

Axon console / control-plane delivery binding for MoveIT must be configured so continuous workers can publish into the real project root (or a git remote). That is outside MoveIT product code; route to Mira (Axon-X).
