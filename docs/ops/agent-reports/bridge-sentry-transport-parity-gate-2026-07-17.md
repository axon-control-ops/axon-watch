# Bridge digest — 2026-07-17 (Sentry transport warning parity gate)

Role: integrations (connectors, watch service, cross-repo wiring)  
Workspace: workspace_axon_watch  
Shift: continuous

## Highest-value action this shift

**Sentry transport warning cross-surface parity gap:** PostHog API transport blips already had
P-A4 parity tests proving inbox, runtime summary, and briefing agree on identity fields and
actionable counts (`open=1`, `critical=0`, `high=0`). Sentry transport failures downgrade to
`warning` severity the same way and had watch-side unit + inbox assembly tests, but no
cross-surface gate — a regression could drop Sentry transport warnings from summary or briefing
while still showing them in the raw inbox, or miscount them as critical/high.

### Change

- `tests/support/monitor_signal_fixture.py` — shared Sentry transport warning inbox fixture
- `tests/test_parity_a4_signal_inbox_consistency.py` — warning parity across inbox, summary,
  and briefing; warning wins over bootstrap; open/critical/high counts asserted
- `tests/test_signal_consistency.py` — Sentry transport warning preserved across inbox and summary
- `tests/test_actionable_inbox_signals.py` — Sentry transport warning suppresses bootstrap in
  assembled inbox

### Receipts

- `python3 -m unittest tests.test_parity_a4_signal_inbox_consistency tests.test_signal_consistency tests.test_actionable_inbox_signals -v` → **31 passed** (3 new Sentry transport warning cases)

### Not acted (deferred)

- Cloudflare **hard cutover** (remote ingress still on `:7734`) — requires Cloudflare remote
  config change outside repo; watch continues soft cutover observation via `tunnel_probe.py`.
