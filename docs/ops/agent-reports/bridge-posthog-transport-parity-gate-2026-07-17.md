# Bridge digest — 2026-07-17 (PostHog transport warning parity gate)

Role: integrations (connectors, watch service, cross-repo wiring)  
Workspace: workspace_axon_watch  
Shift: continuous

## Highest-value action this shift

**PostHog transport warning cross-surface parity gap:** Sentry critical and connector
failure signals had P-A4 parity tests proving inbox, runtime summary, and briefing agree
on identity fields and actionable counts. PostHog API transport blips downgrade to
`warning` severity (not critical/high) and had watch-side unit + inbox assembly tests,
but no cross-surface gate — a regression could drop transport warnings from summary or
briefing while still showing them in the raw inbox, or miscount them as critical.

### Change

- `tests/support/monitor_signal_fixture.py` — shared PostHog transport warning inbox fixture
- `tests/test_parity_a4_signal_inbox_consistency.py` — warning parity across inbox,
  summary, and briefing; warning wins over bootstrap; open/critical/high counts asserted
- `tests/test_signal_consistency.py` — PostHog warning preserved across inbox and summary
- `tests/test_actionable_inbox_signals.py` — warning counts as actionable (open=1,
  critical=0); transport warning suppresses bootstrap in assembled inbox

### Receipts

- `python3 -m unittest tests.test_parity_a4_signal_inbox_consistency tests.test_signal_consistency tests.test_actionable_inbox_signals -v` → **25 passed**

### Not acted (deferred)

- Cloudflare **hard cutover** (remote ingress still on `:7734`) — requires Cloudflare
  remote config change outside repo; watch continues soft cutover observation via
  `tunnel_probe.py`.
