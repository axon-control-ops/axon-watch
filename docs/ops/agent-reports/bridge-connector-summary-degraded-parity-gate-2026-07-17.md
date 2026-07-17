# Bridge digest — 2026-07-17 (connector + summary-degraded parity gate)

Role: integrations (connectors, watch service, cross-repo wiring)  
Workspace: workspace_axon_watch  
Shift: continuous

## Highest-value action this shift

**Connector + summary-degraded cross-surface parity gap:** When required connectors fail,
watch assembly intentionally emits both a connector inbox signal and the
`signal_runtime_summary_degraded` placeholder. Connector/bootstrap and connector/degraded
pairs already had P-A4 gates, but the **real outage shape** (connector + summary-degraded)
had only watch-side inbox integration coverage — a regression could double-count severity,
surface stale bootstrap copy on runtime summary/briefing, or rank summary-degraded above
the live connector signal.

### Change

- `tests/test_parity_a4_signal_inbox_consistency.py` — connector and connector-degraded
  win over summary-degraded across inbox, summary, and briefing; counts asserted
- `tests/test_signal_consistency.py` — same pairing preserved across inbox and summary
- `tests/test_actionable_inbox_signals.py` — summary-degraded excluded from actionable
  counts when a connector signal is present
- `docs/PARITY_A4_SIGNAL_INBOX_CONSISTENCY.md` — documents the paired-outage case

### Receipts

- `python3 -m unittest tests.test_parity_a4_signal_inbox_consistency tests.test_signal_consistency tests.test_actionable_inbox_signals -v` → **45 passed** (5 new cases)

### Not acted (deferred)

- Cloudflare **hard cutover** (remote ingress still on `:7734`) — requires Cloudflare remote
  config change outside repo; watch continues soft cutover observation via `tunnel_probe.py`.
