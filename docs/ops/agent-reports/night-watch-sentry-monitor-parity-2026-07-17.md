# Night Watch digest — 2026-07-17 (Sentry monitor parity)

Role: watcher (signals, connectors, runtime health)  
Workspace: workspace_axon_watch  
Shift: always_on

## Runtime health (live)

| Check | Result |
|---|---|
| Console web `:4173` | ok |
| Control plane health/ready | ok / ready |
| Watch health/ready (`:8788`) | ok / ready |
| Connectors | 4 configured, 4 ok, 0 required unavailable |
| Runtime degraded | inactive |
| Inbox | 1 item — DashPro Sentry critical (3 unresolved Android issues; live and cross-surface consistent) |

## Highest-value action this shift

**Sentry monitor cross-surface parity gap:** Email and connector signals had P-A4 parity tests
proving inbox, runtime summary, and briefing agree on identity fields and actionable counts.
DashPro Sentry monitor failures (`source: watch`, `signal_family: child_project_monitor`) had
watch-side assembly tests but no cross-surface gate — a regression could drop Sentry issue
meta (`sentry_issues`, `sentry_issue_count`) from briefing/runtime summary while still
showing a bare signal in the raw inbox.

### Change

- `tests/support/monitor_signal_fixture.py` — shared Sentry critical inbox fixture with issue sample meta
- `tests/test_parity_a4_signal_inbox_consistency.py` — Sentry monitor parity across inbox,
  summary, and briefing; Sentry wins over bootstrap in actionable counts; meta preserved on all surfaces
- `tests/test_signal_consistency.py` — Sentry monitor signal preserved across inbox and summary with issue meta

### Receipts

- `python3 -m unittest tests.test_parity_a4_signal_inbox_consistency tests.test_signal_consistency -v` → **14 passed**
- `./scripts/dev/check-health.sh` → stack ok, 4 connectors ok, inbox shows live Sentry critical with matching summary/briefing meta

## Watch items (not acted)

- Cloudflare soft cutover (remote ingress still on `:7734`) — integrations ownership for hard cutover.
- Live Sentry critical (Google Sign-In, realtime subscribe, session init) — legitimate child-project signal; left open for DashPro lane.
