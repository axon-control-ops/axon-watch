# Bridge digest — 2026-07-17 (PostHog threshold warning parity gate)

Role: integrations (connectors, watch service, cross-repo wiring)  
Workspace: workspace_axon_watch  
Shift: continuous

## Highest-value action this shift

**PostHog threshold warning (high) cross-surface parity gap:** Sentry threshold
warnings (monitor status=warning without transport blip → severity=high) already had
P-A4 parity gates. PostHog uses the same severity ladder: zero recent events returns
monitor status=warning but maps to **high** severity in the inbox — distinct from
transport blips (warning severity). No cross-surface gate existed; a regression could
miscount these as critical, drop `high_count`, or strip them from summary/briefing.

### Change

- `tests/support/monitor_signal_fixture.py` — shared PostHog threshold warning (high) fixture
- `tests/test_parity_a4_signal_inbox_consistency.py` — threshold warning parity across inbox, summary, and briefing; wins over bootstrap; open/critical/high counts asserted
- `tests/test_signal_consistency.py` — threshold warning preserved across inbox and summary
- `tests/test_actionable_inbox_signals.py` — high count for PostHog threshold warning; bootstrap suppressed when present
- `tests/test_monitor_inbox_integration.py` — assembled inbox upranks PostHog zero-events warning to high
- `tests/test_dashpro_posthog.py` — zero-events probe status + inbox severity mapping

### Receipts

- `python3 -m unittest tests.test_parity_a4_signal_inbox_consistency.ParityA4SignalInboxConsistencyTests.test_posthog_threshold_warning_consistent_across_inbox_summary_and_briefing tests.test_parity_a4_signal_inbox_consistency.ParityA4SignalInboxConsistencyTests.test_posthog_threshold_warning_wins_over_bootstrap_in_summary_and_briefing tests.test_signal_consistency.SignalConsistencyTests.test_control_plane_preserves_posthog_threshold_warning_across_inbox_and_summary -v` → **3 passed**
- `PYTHONPATH=services/axon-watch python3 -m unittest tests.test_monitor_inbox_integration tests.test_dashpro_posthog -v` → **9 passed**

### Not acted (deferred)

- Cloudflare **hard cutover** (remote ingress still on `:7734`) — requires Cloudflare remote
  config change outside repo; watch continues soft cutover observation via `tunnel_probe.py`.
