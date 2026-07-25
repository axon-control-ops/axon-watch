# Ops Scripts

| Script | Purpose |
|---|---|
| `axonhealth.sh` | One-word **`axonhealth`** — probe console + APIs (`check-health.sh`) |
| `axonrestart.sh` | One-word **`axonrestart`** — soft restart always-on systemd units + health |
| `axonrevive.sh` | One-word **`axonrevive`** — force-kill wedged control-plane, restart stack + health |
| `install-bin-wrappers.sh` | Symlink `bin/axonhealth`, `axonrestart`, `axonrevive` into `~/.local/bin/` |
| `change-verify-loop.sh` | Local change → critical-review clause → `npm run verify:contracts` (supports `--watch`, `--head-only`) |
| `validate_deployment_config.py` | Validate dedicated-server topology + infra artifacts |
| `run-service.sh` | Start one service using deployment env (systemd wrapper) |
| `install-user-always-on.sh` | Install/enable user systemd units so the stack stays up on a powered host |
| `planning_bundle_manifest.py` | Write/validate sha256 manifest for `docs/planning/` |
| `sync_planning_mirror_to_axon_local.py` | Push canonical planning bundle to axon-local mirror |

PATH wrappers live in `bin/` and install via `./scripts/ops/install-bin-wrappers.sh` (also run by `install-user-always-on.sh`).

### change-verify-loop

```bash
./scripts/ops/change-verify-loop.sh              # verify current working tree
./scripts/ops/change-verify-loop.sh --head-only  # stash dirty files, verify HEAD commit, restore
./scripts/ops/change-verify-loop.sh --watch      # re-run when the dirty fingerprint changes
```

Logs land under `.axon/change-verify-loop.log` and `.axon/verify-contracts-latest.log`.

Local bootstrap lifecycle remains under `scripts/dev/`. Note: **`./scripts/dev/down.sh` does not stop systemd always-on units** — use `axonrestart` / `axonrevive` on this host.

**Frontend on `:4173`:** after console-web source changes, rebuild then restart:

```bash
npm run build -w @axon-watch/console-web
systemctl --user restart console-web.service
# hard-refresh http://127.0.0.1:4173
```

Dedicated-server spec: `docs/DEDICATED_SERVER_READINESS.md`.
Planning migration spec: `docs/CROSS_REPO_PLANNING_MIGRATION.md`.
Cutover decision: `docs/CUTOVER_DECISION.md` (parity snapshot in `config/parity-snapshot.json`).
