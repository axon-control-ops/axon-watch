# Night Watch digest — 2026-07-17 (email signal parity gate)

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
| Inbox | 1 item — DashPro Sentry critical (cross-surface parity confirmed live) |

Cross-surface live check: inbox, runtime summary, and briefing all agree on
`signal_monitor_dashpro_sentry_recent_issues_critical` with `sentry_issue_count=3`
and `critical_count=1` on summary.

## Highest-value action this shift

**Email signal (high) cross-surface parity gap:** Connector and monitor signals had P-A4
parity tests proving inbox, runtime summary, and briefing agree on identity fields and
actionable counts (`open_count`, `critical_count`, `high_count`), plus bootstrap suppression.
Email triage signals (`source: email`, severity `high`) had consistency tuple tests but no
actionable-count or bootstrap-win gates — a regression could miscount email follow-ups as
critical, drop `high_count`, or leave bootstrap copy visible alongside urgent email items.

### Change

- `tests/test_parity_a4_signal_inbox_consistency.py` — email high-severity actionable counts;
  email wins over bootstrap across summary and briefing
- `tests/test_signal_consistency.py` — email `high_count` / `critical_count` on runtime summary
- `tests/test_actionable_inbox_signals.py` — email high counts as actionable-not-critical;
  bootstrap excluded from actionable summary when email present

### Receipts

- `python3 -m unittest tests.test_parity_a4_signal_inbox_consistency tests.test_signal_consistency tests.test_actionable_inbox_signals -v` → **48 passed**
- `./scripts/dev/check-health.sh` → stack ok; connectors 3 ok / 1 degraded (tunnel); inbox Sentry critical unchanged

## Watch items (not acted)

- Cloudflare soft cutover (remote ingress still on `:7734`) — integrations ownership for hard cutover.
- Live DashPro Sentry critical (Google Sign-In, realtime subscribe, session init) — legitimate signal; left open for DashPro lane.
