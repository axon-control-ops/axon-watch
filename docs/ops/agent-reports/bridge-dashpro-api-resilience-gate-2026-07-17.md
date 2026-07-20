# Bridge digest — 2026-07-17 (DashPro API resilience gate)

Role: integrations (connectors, watch service, cross-repo wiring)  
Workspace: workspace_axon_watch  
Shift: continuous

## Highest-value action this shift

**DashPro monitor API resilience gap:** Transient network failures from PostHog,
Sentry, and Supabase Storage probes were paging as `critical` (or upranking to
inbox `high`). A timeout blip should stay `warning` monitor status and `warning`
inbox severity — distinct from auth/quota criticals and volume-threshold highs.

### Change

- `services/axon-watch/app/monitors/dashpro_posthog.py` — transport → warning
- `services/axon-watch/app/monitors/dashpro_sentry.py` — transport → warning
- `services/axon-watch/app/monitors/dashpro_supabase_storage.py` — transport → warning;
  402 restrictions stay critical
- `services/axon-watch/app/signals/monitor_signal.py` — shared ` API query failed:`
  marker keeps transport (and Sentry scope gaps) at inbox severity warning
- `tests/test_dashpro_posthog.py` / `tests/test_dashpro_sentry.py` /
  `tests/test_dashpro_supabase_storage.py` — transport regression coverage
- `tests/test_dashpro_monitor_slice.py` / `tests/test_actionable_inbox_signals.py` —
  severity + actionable count coverage
- `scripts/verify/test16-dashpro-monitors.sh` — runs PostHog/Sentry/Supabase units

### Receipts

- `PYTHONPATH=services/axon-watch python3 -m unittest tests.test_dashpro_posthog tests.test_dashpro_sentry tests.test_dashpro_supabase_storage tests.test_dashpro_monitor_slice tests.test_actionable_inbox_signals -v` → **passed**

### Not acted (deferred)

- Cloudflare **hard cutover** (remote ingress still on `:7734`) — requires Cloudflare
  remote config change outside repo; watch continues soft cutover observation via
  `tunnel_probe.py`.
