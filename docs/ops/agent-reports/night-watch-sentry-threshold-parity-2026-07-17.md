# Night Watch digest — 2026-07-17 (Sentry threshold warning parity)

Role: watcher (signals, connectors, runtime health)  
Workspace: workspace_axon_watch  
Shift: always_on

## Runtime health (live)

| Check | Result |
|---|---|
| Console web `:4173` | ok |
| Control plane health/ready | ok / ready |
| Watch health/ready (`:8788`) | ok / ready |
| Connectors | 4 configured, 3 ok, 1 degraded (optional Cloudflare tunnel), 0 required unavailable |
| Runtime degraded | inactive |
| Inbox | 1 item — DashPro Sentry critical (live child-project signal) |

## Highest-value action this shift

**Sentry threshold warning (high) cross-surface parity gap:** Critical Sentry monitor
failures and transport blips (warning severity) already had P-A4 parity gates. When
Sentry returns enough unresolved issues to hit the warning threshold but not critical,
watch maps `monitor_status=warning` to **high** severity — same signal_id suffix as
transport blips but different urgency. No cross-surface gate existed; a regression could
miscount these as critical, drop `high_count`, or strip issue meta from summary/briefing.

### Change

- `tests/support/monitor_signal_fixture.py` — shared Sentry threshold warning (high) fixture with issue sample meta
- `tests/test_parity_a4_signal_inbox_consistency.py` — threshold warning parity across inbox, summary, and briefing; wins over bootstrap; open/critical/high counts asserted
- `tests/test_signal_consistency.py` — threshold warning preserved across inbox and summary with issue meta
- `tests/test_actionable_inbox_signals.py` — high count for threshold warning; bootstrap suppressed when present
- `tests/test_monitor_inbox_integration.py` — assembled inbox upranks threshold warning to high

### Receipts

- `python3 -m unittest tests.test_parity_a4_signal_inbox_consistency tests.test_signal_consistency tests.test_actionable_inbox_signals -v` → **40 passed**
- `PYTHONPATH=services/axon-watch python3 -m unittest tests.test_monitor_inbox_integration -v` → **5 passed**
- Live runtime: required connectors ok, degraded inactive, inbox Sentry critical unchanged

## Watch items (not acted)

- Cloudflare soft cutover (remote ingress still on `:7734`) — integrations ownership for hard cutover.
- Live DashPro Sentry critical — legitimate child-project signal; left open for DashPro lane.
