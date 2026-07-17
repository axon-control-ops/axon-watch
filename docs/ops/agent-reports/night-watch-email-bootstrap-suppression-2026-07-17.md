# Night Watch digest — 2026-07-17 (email bootstrap suppression)

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
| Inbox | 1 item — DashPro Sentry critical (cross-surface parity confirmed) |

## Highest-value action this shift

**Bootstrap noise alongside email triage:** Connector and monitor failures already suppressed
`signal_watch_bootstrap_ready`, but email triage signals did not — an inbox with only a
legitimate email follow-up still showed contradictory "Watch bootstrap ready" copy.

### Change

- `services/axon-watch/app/signals/inbox_filters.py` — extend `should_emit_bootstrap_signal`
  to omit bootstrap when email items are present
- `services/axon-watch/app/signals/store.py` — pass assembled email items into bootstrap gate
- `tests/test_actionable_inbox_signals.py` — unit + assembly tests for email suppression

### Receipts

- `PYTHONPATH=services/axon-watch python3 -m unittest tests.test_actionable_inbox_signals tests.test_email_signal tests.test_connector_inbox_integration tests.test_monitor_inbox_integration -v` → **27 passed**
- `./scripts/dev/check-health.sh` → stack ok
- axon-watch restarted; live inbox shows Sentry critical only (no bootstrap item)

## Watch items (not acted)

- Cloudflare soft cutover (remote ingress still on `:7734`) — integrations ownership for hard cutover.
- Live DashPro Sentry critical — legitimate child-project signal; left open for DashPro lane.
