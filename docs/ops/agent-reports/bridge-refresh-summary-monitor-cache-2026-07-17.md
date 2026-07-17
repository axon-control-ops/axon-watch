# Bridge digest — 2026-07-17 (refresh_summary monitor cache)

Role: integrations (connectors, watch service, cross-repo wiring)  
Workspace: workspace_axon_watch  
Shift: continuous

## Highest-value action this shift

**Monitor cache invalidation on `refresh_summary`:** connector probe cache was cleared
when operators ran `refresh_summary`, but DashPro monitor probes stayed on the warm TTL
cache — inbox monitor signals could remain stale after an explicit refresh.

### Change

- `services/axon-watch/app/commands/executor.py` — `execute_refresh_summary` also calls
  `reset_monitor_probe_cache()` before rebuilding summary
- `tests/test_dashpro_monitor_cache.py` — regression test for refresh-driven live probe
- `.env.example`, `docs/WATCH_COMMAND_EVENT_DEPTH.md`, `docs/internal/AGENT-POLISH-NOTES.md`
  — document both caches cleared on refresh

### Receipts

- `PYTHONPATH=services/axon-watch python3 -m unittest tests.test_dashpro_monitor_cache -v` → **4 passed**

### Not acted (deferred)

- Cloudflare **hard cutover** (remote ingress still on `:7734`) — requires Cloudflare
  remote config change outside repo; watch continues soft cutover observation via
  `tunnel_probe.py`.
