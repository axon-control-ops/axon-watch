# Bridge digest — 2026-07-17 (refresh_summary dual-cache gate)

Role: integrations (connectors, watch service, cross-repo wiring)  
Workspace: workspace_axon_watch  
Shift: continuous

## Highest-value action this shift

**`refresh_summary` dual-cache regression gate:** executor clears connector and monitor
probe caches on `refresh_summary`, but only the monitor side had a unit regression test
and TEST-4 did not exercise either cache-invalidation path.

### Change

- `tests/test_connector_probe_cache.py` — `test_execute_refresh_summary_clears_connector_cache`
- `scripts/verify/test4-watch-command-event-depth.sh` — step 2 runs both refresh-summary
  cache regression tests (connector + monitor)
- `docs/WATCH_COMMAND_EVENT_DEPTH.md` — verification block documents the paired tests

### Receipts

- `PYTHONPATH=services/axon-watch python3 -m unittest tests.test_connector_probe_cache tests.test_dashpro_monitor_cache -v` → **10 passed**
- `./scripts/dev/check-health.sh` → console, control-plane, watch, runtime summary, inbox ok
- Live connectors: 4 configured, 4 ok, 0 required unavailable

### Not acted (deferred)

- Cloudflare **hard cutover** (remote ingress still on `:7734`) — requires Cloudflare
  remote config change outside repo; watch continues soft cutover observation via
  `tunnel_probe.py`.
