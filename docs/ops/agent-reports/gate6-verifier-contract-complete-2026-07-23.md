# Gate 6 — Mandatory verifier contract (completion slice)

**Date:** 2026-07-23  
**Branch:** `feat/gate6-verifier`

## Implemented

- Fail-closed acceptance evidence for task-bound runs (first slice)
- `project.axon.yaml` + `config/project-contracts/axon-watch.project.axon.yaml`
- Adapters: `node_vue`, `python_fastapi`, `android_gradle` (unsupported → inspect-only)
- Diff policy: allowed paths, forbidden globs, secret patterns, diff-budget path count
- Immutable verifier identity (`verifier` ≠ implementer) for acceptance evaluation
- Structured check plan/evaluation (`verifier_checks.py`) + companion check-output receipts

## Tests

- `tests.test_gate6_verifier_contract` (5)
- `tests.test_gate6_project_contract` (6)

## Exit criteria

| Criterion | Status |
| --- | --- |
| No task-bound run → review-ready without acceptance | Met |
| Failed checks / policy findings block acceptance | Met (unit) |
| Separate verifier identity | Met |
| project.axon.yaml adapters certified for Node/Vue, Python/FastAPI, Android/Gradle | Met (contract + adapter registry) |
| Live worker finalize auto-runs check commands | Partial — evaluation API ready; command execution still operator/CI driven |

## Residual

- Execute check commands inside the control-plane worker sandbox with captured stdout receipts
- Block Gate 8 PR creation through the same enforce hook
