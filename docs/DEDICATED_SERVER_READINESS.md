# Dedicated-Server Readiness

## Purpose

Proves the Axon-X three-service split can run outside the local bootstrap path
with config-driven URLs, documented startup order, and infra artifacts for
supervision and reverse proxy — without requiring a live dedicated host in CI.

## Artifacts

| Path | Role |
|---|---|
| `config/deployment-topology.json` | Startup order + service exposure rules |
| `config/deployment.env.example` | Dedicated-host env template (no loopback public URL) |
| `scripts/ops/validate_deployment_config.py` | Validates topology + infra files |
| `scripts/ops/run-service.sh` | systemd-friendly service launcher |
| `infra/systemd/*.service` | Unit files (watch → control-plane → console-web) |
| `infra/caddy/Caddyfile.example` | Public `/api` proxy; watch stays internal |
| `infra/docker-compose.dedicated.yml` | Reference compose topology |

## Startup order

1. storage paths available  
2. `axon-watch`  
3. `control-plane`  
4. `console-web`  
5. reverse proxy / TLS  

## Config rules (v1)

- Public URL (`AXON_WATCH_PUBLIC_BASE_URL`) must not use loopback on dedicated hosts
- `AXON_WATCH_STATE_DIR` must be absolute on dedicated hosts
- Watch internal API (`/internal/watch/*`) is **not** exposed via Caddy example
- Control-plane CORS accepts `AXON_WATCH_CORS_ORIGINS` (comma-separated)

## Readiness signals

Control-plane `/api/readiness` includes:

- `mode` — `bootstrap` or `dedicated`
- `watch_base_url` — from env
- `state_dir` — from env

Watch `/internal/watch/readiness` includes `state_dir`.

## Verification

```bash
npm run verify:test8
# or
./scripts/verify/test8-dedicated-server-readiness.sh
python3 ./scripts/ops/validate_deployment_config.py
```

## Not in v1

- Live TLS provisioning on a real dedicated machine
- Auth beyond placeholder mode
- Kubernetes manifests
- Automated migrate-to-server playbook

Next locked item: **Cross-repo planning migration**.
