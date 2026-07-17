# Bridge digest — 2026-07-17 (monitor cache gate)

Role: integrations (connectors, watch service, cross-repo wiring)  
Workspace: workspace_axon_watch  
Shift: continuous

## Highest-value action this shift

**DashPro monitor probe cache gate:** TTL caching shipped in watch (`probe_monitor_records`,
`reset_monitor_probe_cache` in `dashpro_monitor.py`) with unit tests in
`tests/test_dashpro_monitor_cache.py`, but the module was not wired into the contract
runner or TEST-16 gate — same gap connector probe cache had earlier today.

### Change

- `scripts/verify/run_contract_unit_tests.sh` — isolated axon-watch slice for
  `tests.test_dashpro_monitor_cache`
- `scripts/verify/test16-dashpro-monitors.sh` — step 2 runs monitor cache tests
- `.env.example` — document `AXON_WATCH_MONITOR_CACHE_TTL_SECONDS`

### Receipts

- `PYTHONPATH=services/axon-watch python3 -m unittest tests.test_dashpro_monitor_cache -v` → **3 passed**
- Sentry resolve already clears monitor cache on successful resolve (`sentry_resolve_service.py`)

### Not acted (deferred)

- Cloudflare **hard cutover** (remote ingress still on `:7734`) — requires Cloudflare
  remote config change outside repo; watch continues soft cutover observation via
  `tunnel_probe.py`.
