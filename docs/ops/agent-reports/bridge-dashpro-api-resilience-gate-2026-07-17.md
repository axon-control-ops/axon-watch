# Bridge digest — 2026-07-17 (DashPro API resilience gate)

Role: integrations (connectors, watch service, cross-repo wiring)  
Workspace: workspace_axon_watch  
Shift: continuous

## Highest-value action this shift

**DashPro monitor API resilience gate:** PostHog and Sentry monitor checks now downgrade
transient network failures to `warning` instead of paging as `critical`, but the
PostHog regression lived in an orphaned test module and Sentry had no matching unit test.
Neither module was wired into TEST-16 or the contract runner.

### Change

- `tests/test_dashpro_sentry.py` — Sentry happy-path + transport-failure regression
- `tests/test_dashpro_posthog.py` — refactor to setUp/tearDown isolation (matches probe-cache tests)
- `scripts/verify/test16-dashpro-monitors.sh` — step 2 runs PostHog + Sentry API tests
- `scripts/verify/run_contract_unit_tests.sh` — isolated slice for both modules

### Receipts

- `PYTHONPATH=services/axon-watch python3 -m unittest tests.test_dashpro_posthog tests.test_dashpro_sentry -v` → **4 passed**
- `python3 -m pytest tests/test_email_signal.py tests/test_dashpro_posthog.py tests/test_dashpro_sentry.py tests/test_dashpro_monitor_cache.py -q` → **17 passed**

### Not acted (deferred)

- Cloudflare **hard cutover** (remote ingress still on `:7734`) — requires Cloudflare
  remote config change outside repo; watch continues soft cutover observation via
  `tunnel_probe.py`.
