# Bridge digest — 2026-07-17 (reprobe cold-cache seed)

Role: integrations (connectors, watch service, cross-repo wiring)  
Workspace: workspace_axon_watch  
Shift: continuous

## Highest-value action this shift

**Reprobe cold-cache seed:** `reprobe_connector` probed one connector live but
`store_connector_probe_record` no-oped when the TTL snapshot was still cold (no prior
summary/connectors read). The command receipt was correct, yet the next cached read
could still miss the targeted upsert until a full live sweep ran.

### Change

- `services/axon-watch/app/connectors/summary.py` — seed a full live snapshot when
  `store_connector_probe_record` runs on a cold cache, then upsert the reprobe row
- `tests/test_connector_probe_cache.py` — `test_store_connector_probe_record_seeds_cold_cache`
- `docs/WATCH_CONNECTORS.md` — probe caching note updated
- `docs/internal/AGENT-POLISH-NOTES.md` — reprobe invalidation note aligned

### Receipts

- `PYTHONPATH=services/axon-watch python3 -m unittest tests.test_connector_probe_cache -v` → **9 passed**
- `python3 -m unittest tests.test_watch_commands_events.WatchCommandsAndEventsTests.test_reprobe_connector_command_returns_completed_receipt -v` → **ok**
- `./scripts/dev/check-health.sh` → console, control-plane, watch, runtime summary, inbox ok
- Live connectors: 4 configured, 4 ok, 0 required unavailable

### Not acted (deferred)

- Cloudflare **hard cutover** (remote ingress still on `:7734`) — requires Cloudflare
  remote config change outside repo; watch continues soft cutover observation via
  `tunnel_probe.py`.
