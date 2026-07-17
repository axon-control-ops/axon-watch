# Bridge digest — 2026-07-17 (connector inbox integration gate)

Role: integrations (connectors, watch service, cross-repo wiring)  
Workspace: workspace_axon_watch  
Shift: continuous

## Highest-value action this shift

**Connector inbox assembly regression gate:** `connector_inbox_item` unit tests shipped earlier
today, but nothing verified that `get_inbox_snapshot` actually surfaces connector failures in
the assembled inbox, omits optional-only noise, or keeps the summary-degraded placeholder when
required connector truth is untrusted.

### Change

- `tests/test_connector_inbox_integration.py` — 3 cases (required degraded in inbox, optional
  failure omitted, untrusted required keeps summary-degraded + connector signal)
- `scripts/verify/run_contract_unit_tests.sh` — run `tests.test_connector_inbox_integration` in
  isolated watch signal slice
- `scripts/verify/test3-watch-connectors.sh` — step 2 includes inbox integration + assembly tests
- `scripts/verify/test25-connector-parity-bundle.sh` — step 3 includes inbox integration +
  assembly tests
- `docs/WATCH_CONNECTORS.md` — verification block lists inbox integration + assembly modules

### Receipts

- `PYTHONPATH=services/axon-watch python3 -m unittest tests.test_connector_inbox_integration -v` → **3 passed**
- `PYTHONPATH=services/axon-watch python3 -m unittest tests.test_connector_signal tests.test_watch_inbox_assembly -v` → **9 passed**

### Not acted (deferred)

- Cloudflare **hard cutover** (remote ingress still on `:7734`) — requires Cloudflare remote
  config change outside repo; watch continues soft cutover observation via `tunnel_probe.py`.
