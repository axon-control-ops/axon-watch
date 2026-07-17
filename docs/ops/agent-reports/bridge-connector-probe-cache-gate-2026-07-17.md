# Bridge digest — 2026-07-17

Role: integrations (connectors, watch service, cross-repo wiring)  
Workspace: workspace_axon_watch  
Shift: continuous

## Highest-value action this shift

**Connector probe cache gate:** probe TTL caching shipped in watch (`probe_all_connectors`,
`store_connector_probe_record`, `reset_connector_probe_cache`) but the dedicated unit
module was only referenced in docs — not in TEST-3, TEST-25, or contract unit tests.

### Change

- `scripts/verify/run_contract_unit_tests.sh` — isolated axon-watch slice for
  `tests.test_connector_probe_cache`
- `scripts/verify/test3-watch-connectors.sh` — step 2 runs probe cache tests
- `scripts/verify/test25-connector-parity-bundle.sh` — step 3 runs probe cache tests

### Receipts

- `PYTHONPATH=services/axon-watch python3 -m unittest tests.test_connector_probe_cache -v` → **5 passed**
- Docs already matched: `docs/WATCH_CONNECTORS.md` verification block

### Not acted (deferred)

- Cloudflare **hard cutover** (remote ingress still on `:7734` while public health is
  Axon-X) — requires Cloudflare remote config change outside repo; watch continues soft
  cutover observation via `tunnel_probe.py`.
