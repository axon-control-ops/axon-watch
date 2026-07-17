# Bridge digest — 2026-07-17 (reprobe cold-cache gate)

Role: integrations (connectors, watch service, cross-repo wiring)  
Workspace: workspace_axon_watch  
Shift: continuous

## Highest-value action this shift

**Reprobe cold-cache regression gate:** `store_connector_probe_record` now seeds a full
snapshot when the TTL cache is cold, but only the store-level unit test guarded that
path. The executor-level reprobe command (catalog + tunnel) and TEST-4 gate still
exercised warm-cache upserts only, so a regression could slip through at the command
boundary.

### Change

- `tests/test_connector_probe_cache.py` — `test_execute_reprobe_connector_seeds_cold_cache`,
  `test_execute_reprobe_tunnel_seeds_cold_cache`
- `scripts/verify/test4-watch-command-event-depth.sh` — step 2 runs cold + warm reprobe
  cache regressions
- `docs/WATCH_COMMAND_EVENT_DEPTH.md` — verification block lists cold-cache reprobe tests
- `docs/WATCH_CONNECTORS.md` — verification block lists cold-cache reprobe tests
- `tests/test_test4_watch_command_event_acceptance.py` — reprobe acceptance asserts
  `/api/connectors` matches command receipt status

### Receipts

- `PYTHONPATH=services/axon-watch python3 -m unittest tests.test_connector_probe_cache -v` → **11 passed**
- `PYTHONPATH=services/axon-watch python3 -m unittest \
  tests.test_connector_probe_cache.ConnectorProbeCacheTests.test_execute_reprobe_connector_seeds_cold_cache \
  tests.test_connector_probe_cache.ConnectorProbeCacheTests.test_execute_reprobe_tunnel_seeds_cold_cache \
  tests.test_connector_probe_cache.ConnectorProbeCacheTests.test_execute_reprobe_connector_updates_warm_cache \
  tests.test_connector_probe_cache.ConnectorProbeCacheTests.test_execute_reprobe_tunnel_updates_warm_cache \
  tests.test_connector_probe_cache.ConnectorProbeCacheTests.test_execute_refresh_summary_clears_connector_cache \
  tests.test_dashpro_monitor_cache.DashProMonitorCacheTests.test_execute_refresh_summary_clears_monitor_cache \
  -v` → **6 passed**
- `python3 -m unittest tests.test_test4_watch_command_event_acceptance -v` → live acceptance ok
- `./scripts/dev/check-health.sh` → console, control-plane, watch, runtime summary, inbox ok

### Not acted (deferred)

- Cloudflare **hard cutover** (remote ingress still on `:7734`) — requires Cloudflare
  remote config change outside repo; watch continues soft cutover observation via
  `tunnel_probe.py`.
