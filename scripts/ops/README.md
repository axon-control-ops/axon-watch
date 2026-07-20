# Ops Scripts

| Script | Purpose |
|---|---|
| `axonhealth.sh` | One-word **`axonhealth`** — probe console + APIs (`check-health.sh`) |
| `axonrestart.sh` | One-word **`axonrestart`** — soft restart always-on systemd units + health |
| `axonrevive.sh` | One-word **`axonrevive`** — force-kill wedged control-plane, restart stack + health |
| `install-bin-wrappers.sh` | Symlink `bin/axonhealth`, `axonrestart`, `axonrevive` into `~/.local/bin/` |
| `validate_deployment_config.py` | Validate dedicated-server topology + infra artifacts |
| `run-service.sh` | Start one service using deployment env (systemd wrapper) |
| `install-user-always-on.sh` | Install/enable user systemd units so the stack stays up on a powered host |
| `planning_bundle_manifest.py` | Write/validate sha256 manifest for `docs/planning/` |
| `sync_planning_mirror_to_axon_local.py` | Push canonical planning bundle to axon-local mirror |

PATH wrappers live in `bin/` and install via `./scripts/ops/install-bin-wrappers.sh` (also run by `install-user-always-on.sh`).

Local bootstrap lifecycle remains under `scripts/dev/`. Note: **`./scripts/dev/down.sh` does not stop systemd always-on units** — use `axonrestart` / `axonrevive` on this host.

Dedicated-server spec: `docs/DEDICATED_SERVER_READINESS.md`.
Planning migration spec: `docs/CROSS_REPO_PLANNING_MIGRATION.md`.
Cutover decision: `docs/CUTOVER_DECISION.md` (parity snapshot in `config/parity-snapshot.json`).
