# P-D3 — Dedicated-Host Smoke

## Deliverable

Simulated dedicated-host readiness smoke proving config-driven deployment mode,
absolute state paths, and non-loopback public URLs — without requiring a live
dedicated machine in CI.

## v1 scope

### In scope

- `/api/readiness` exposes `mode`, `watch_base_url`, `state_dir`, `public_base_url`
- Contract checker: `scripts/verify/check_dedicated_deployment_smoke.py`
- Integration tests with patched env simulating dedicated deployment
- Regression: `tests/test_deployment_readiness`, `tests/test_test8_dedicated_server_acceptance`

### Acceptable v1 degradation

- CI uses simulated dedicated env (temp absolute `AXON_WATCH_STATE_DIR`)
- Live TLS and real host provisioning remain out of scope

### Out of scope

- Automated migrate-to-server playbook
- Kubernetes manifests

## Gate

```bash
npm run verify:parity-d3
```

## Promotion

On gate pass, update `config/parity-closure-order.json` → `P-D3.status = done`,
`next_slice = P-D4`.
