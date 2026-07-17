# Night Watch digest — 2026-07-17 (connector signal parity)

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

**Connector signal cross-surface parity gap:** Email and monitor signals had P-A4 parity
tests proving inbox, runtime summary, and briefing agree on identity fields and actionable
counts. Required connector failure signals (`source: connector`) had unit and assembly tests
on the watch side but no cross-surface consistency gate — a regression could drop connector
outages from briefing/runtime summary while still showing them in the raw inbox.

### Change

- `tests/support/connector_signal_fixture.py` — shared connector failure inbox fixture
- `tests/test_parity_a4_signal_inbox_consistency.py` — connector parity across inbox,
  summary, and briefing; connector wins over bootstrap in actionable counts
- `tests/test_signal_consistency.py` — connector signal preserved across inbox and summary

### Receipts

- `python3 -m unittest tests.test_parity_a4_signal_inbox_consistency tests.test_signal_consistency -v` → **11 passed**
- `./scripts/dev/check-health.sh` → stack ok, 4 connectors ok, inbox empty

## Watch items (not acted)

- Cloudflare soft cutover (remote ingress still on `:7734`) — integrations ownership for hard cutover.
- Optional `axon_local` down chip in status bar — polish backlog item.
