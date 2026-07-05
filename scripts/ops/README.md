# Ops Scripts

| Script | Purpose |
|---|---|
| `validate_deployment_config.py` | Validate dedicated-server topology + infra artifacts |
| `run-service.sh` | Start one service using deployment env (systemd wrapper) |
| `planning_bundle_manifest.py` | Write/validate sha256 manifest for `docs/planning/` |
| `sync_planning_mirror_to_axon_local.py` | Push canonical planning bundle to axon-local mirror |

Local bootstrap lifecycle remains under `scripts/dev/`.

Dedicated-server spec: `docs/DEDICATED_SERVER_READINESS.md`.
Planning migration spec: `docs/CROSS_REPO_PLANNING_MIGRATION.md`.
Cutover decision: `docs/CUTOVER_DECISION.md` (parity snapshot in `config/parity-snapshot.json`).
