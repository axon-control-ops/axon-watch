# Bridge digest — 2026-07-17 (connector bootstrap suppression gate)

Role: integrations (connectors, watch service, cross-repo wiring)  
Workspace: workspace_axon_watch  
Shift: continuous

## Highest-value action this shift

**Connector bootstrap suppression CI gap:** Night Watch shipped bootstrap suppression when
required connector probes fail (`should_emit_bootstrap_signal` + inbox assembly), with unit
tests in `tests/test_actionable_inbox_signals.py`. Those tests only ran under TEST-16
(DashPro monitors), not the connector contract slice or TEST-3/TEST-25 gates — so a
regression could hide contradictory "bootstrap ready" copy during connector outages.

### Change

- `scripts/verify/run_contract_unit_tests.sh` — run `tests.test_actionable_inbox_signals`
  in isolated watch signal slice
- `scripts/verify/test3-watch-connectors.sh` — step 2 includes actionable inbox filter tests
- `scripts/verify/test25-connector-parity-bundle.sh` — step 3 includes actionable inbox tests
- `docs/WATCH_CONNECTORS.md` — verification block lists actionable inbox module

### Receipts

- `PYTHONPATH=services/axon-watch python3 -m unittest tests.test_actionable_inbox_signals -v` → **6 passed**
- `PYTHONPATH=services/axon-watch python3 -m unittest \
  tests.test_connector_signal tests.test_connector_inbox_integration \
  tests.test_actionable_inbox_signals tests.test_watch_inbox_assembly -v` → **18 passed**
- `./scripts/dev/check-health.sh` → console, control-plane, watch, runtime summary, inbox ok
- Live connectors: 4 configured, 4 ok, 0 required unavailable

### Not acted (deferred)

- Cloudflare **hard cutover** (remote ingress still on `:7734`) — requires Cloudflare
  remote config change outside repo; watch continues soft cutover observation via
  `tunnel_probe.py`.
