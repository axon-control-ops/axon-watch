# Bridge digest — 2026-07-17 (monitor inbox integration gate)

Role: integrations (connectors, watch service, cross-repo wiring)  
Workspace: workspace_axon_watch  
Shift: continuous

## Highest-value action this shift

**Monitor inbox assembly regression gate:** DashPro monitor projection unit tests and one
bootstrap-suppression case existed, but nothing verified that `get_inbox_snapshot` surfaces
critical monitor failures, omits ok/skipped noise, downranks transport API blips to warning
severity, or preserves Sentry issue meta through assembly.

### Change

- `tests/test_monitor_inbox_integration.py` — 4 cases (critical in inbox, ok/skipped omitted,
  transport downrank, Sentry issues meta)
- `scripts/verify/run_contract_unit_tests.sh` — run `tests.test_monitor_inbox_integration` in
  isolated watch monitor slice
- `scripts/verify/test16-dashpro-monitors.sh` — step 2 includes monitor inbox integration tests

### Receipts

- `PYTHONPATH=services/axon-watch python3 -m unittest tests.test_monitor_inbox_integration -v` → **4 passed**
- `PYTHONPATH=services/axon-watch python3 -m unittest tests.test_dashpro_monitor_slice tests.test_monitor_inbox_integration tests.test_actionable_inbox_signals -v` → **15 passed**

### Not acted (deferred)

- Cloudflare **hard cutover** (remote ingress still on `:7734`) — requires Cloudflare remote
  config change outside repo; watch continues soft cutover observation via `tunnel_probe.py`.
