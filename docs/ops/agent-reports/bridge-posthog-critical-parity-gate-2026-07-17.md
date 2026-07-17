# Bridge digest — 2026-07-17 (PostHog critical parity gate)

Role: integrations (connectors, watch service, cross-repo wiring)  
Workspace: workspace_axon_watch  
Shift: continuous

## Highest-value action this shift

**PostHog critical (auth/access) cross-surface parity gap:** Sentry critical monitor
failures already had cross-surface gates. PostHog auth rejection (401), project
denial (403), and other non-200 API failures map to monitor status=`critical` and
inbox severity=`critical` — distinct from transport blips (warning) and zero-events
thresholds (high). No cross-surface gate existed; a regression could miscount these
as high/warning, drop `critical_count`, or strip them from summary/briefing.

### Change

- `tests/support/monitor_signal_fixture.py` — shared PostHog critical fixture
- `tests/test_parity_a4_signal_inbox_consistency.py` — critical parity across inbox,
  summary, and briefing; wins over bootstrap; open/critical/high counts asserted
- `tests/test_signal_consistency.py` — critical preserved across inbox and summary
- `tests/test_actionable_inbox_signals.py` — critical counts; bootstrap suppressed
- `tests/test_monitor_inbox_integration.py` — assembled inbox keeps PostHog auth
  failure at critical
- `tests/test_dashpro_posthog.py` — 401 probe status + inbox severity mapping
- `docs/PARITY_A4_SIGNAL_INBOX_CONSISTENCY.md` — documents PostHog critical coverage

### Receipts

- `python3 -m unittest …posthog_critical…` (parity + consistency) → **3 passed**
- `PYTHONPATH=services/axon-watch python3 -m unittest …posthog_critical…` (actionable +
  inbox integration + PostHog probe) → **4 passed**
- Total new cases this shift: **7 passed**

### Not acted (deferred)

- Cloudflare **hard cutover** (remote ingress still on `:7734`) — requires Cloudflare remote
  config change outside repo; watch continues soft cutover observation via `tunnel_probe.py`.
