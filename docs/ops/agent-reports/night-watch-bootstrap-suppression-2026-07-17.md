# Night Watch digest — 2026-07-17 (bootstrap suppression)

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
| Inbox | empty (healthy stack) |

## Highest-value action this shift

**Bootstrap noise during connector failures:** When a required connector probe failed,
`get_inbox_snapshot` still emitted `signal_watch_bootstrap_ready` alongside the
connector failure and summary-degraded placeholder — contradictory "ready" copy during
an active outage.

### Change

- `services/axon-watch/app/signals/inbox_filters.py` — suppress bootstrap when connector
  inbox items are present (same rule as live monitor items)
- `services/axon-watch/app/signals/store.py` — pass connector items into bootstrap gate
- `tests/test_actionable_inbox_signals.py` — connector suppression cases + setUp/tearDown
  isolation
- `tests/test_connector_inbox_integration.py` — assert bootstrap omitted on connector failure;
  setUp/tearDown isolation

### Receipts

- `python3 -m pytest tests/test_actionable_inbox_signals.py tests/test_connector_inbox_integration.py tests/test_email_signal.py tests/test_connector_signal.py -q` → **28 passed**
- 3 consecutive isolated runs: `PYTHONPATH=services/axon-watch python3 -m unittest tests.test_actionable_inbox_signals tests.test_connector_inbox_integration tests.test_email_signal -q` → **19 passed** each
- `./scripts/dev/check-health.sh` → stack ok, 4 connectors ok, inbox empty

## Watch items (not acted)

- Cloudflare soft cutover (remote ingress still on `:7734`) — integrations ownership for hard cutover.
- Optional `axon_local` down chip in status bar — polish backlog item.
