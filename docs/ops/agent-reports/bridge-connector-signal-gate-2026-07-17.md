# Bridge digest — 2026-07-17 (connector signal gate)

Role: integrations (connectors, watch service, cross-repo wiring)  
Workspace: workspace_axon_watch  
Shift: continuous

## Highest-value action this shift

**Connector inbox signal regression gate:** `connector_inbox_item` / `connector_inbox_items`
encode required-vs-optional and severity rules for connector probe failures, but had no
dedicated unit tests or verify-gate coverage. A regression could silently drop required
connector failures from Attention or page on optional probes.

### Change

- `tests/test_connector_signal.py` — 5 cases (ok skip, optional skip, degraded high,
  unavailable critical, batch filter)
- `tests/test_connector_probe_cache.py` — removed duplicate
  `test_execute_reprobe_connector_seeds_cold_cache` method
- `scripts/verify/run_contract_unit_tests.sh` — run `tests.test_connector_signal` in
  isolated watch signal slice
- `scripts/verify/test3-watch-connectors.sh` — step 2 includes connector signal tests
- `scripts/verify/test25-connector-parity-bundle.sh` — step 3 includes connector signal tests
- `docs/WATCH_CONNECTORS.md` — verification block lists connector signal module

### Receipts

- `PYTHONPATH=services/axon-watch python3 -m unittest tests.test_connector_signal -v` → **5 passed**
- `PYTHONPATH=services/axon-watch python3 -m unittest tests.test_connector_probe_cache -v` → **10 passed**

### Not acted (deferred)

- Cloudflare **hard cutover** (remote ingress still on `:7734`) — requires Cloudflare
  remote config change outside repo; watch continues soft cutover observation via
  `tunnel_probe.py`.
