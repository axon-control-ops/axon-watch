# Bridge digest — 2026-07-17 (connector degraded high-severity parity gate)

Role: integrations (connectors, watch service, cross-repo wiring)  
Workspace: workspace_axon_watch  
Shift: continuous

## Highest-value action this shift

**Connector degraded (high) cross-surface parity gap:** Required connector `unavailable`
failures already had P-A4 parity tests with `critical_count=1`. Required `degraded` probes
emit **high** severity (for example HTTP 503) and had watch-side unit + inbox assembly tests,
but no cross-surface gate — a regression could miscount them as critical, drop them from
runtime summary/briefing, or leave bootstrap copy visible during a partial outage.

### Change

- `tests/support/connector_signal_fixture.py` — shared degraded (high) connector fixture
- `tests/test_parity_a4_signal_inbox_consistency.py` — degraded parity across inbox,
  summary, and briefing; degraded wins over bootstrap; open/critical/high counts asserted
- `tests/test_signal_consistency.py` — degraded connector preserved across inbox and summary
- `tests/test_actionable_inbox_signals.py` — degraded connector suppresses bootstrap in
  assembled inbox

### Receipts

- `python3 -m unittest tests.test_parity_a4_signal_inbox_consistency tests.test_signal_consistency tests.test_actionable_inbox_signals -v` → **35 passed** (4 new degraded cases)

### Not acted (deferred)

- Cloudflare **hard cutover** (remote ingress still on `:7734`) — requires Cloudflare remote
  config change outside repo; watch continues soft cutover observation via `tunnel_probe.py`.
