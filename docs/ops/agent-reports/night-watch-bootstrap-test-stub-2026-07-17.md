# Night Watch digest — 2026-07-17 (bootstrap test stub isolation)

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
| Inbox | 1 item — DashPro Sentry critical (legitimate child-project signal) |

Connector notes:

- Cloudflare tunnel is **degraded** (process up; public health still hits axon-local on `:7734`). Required connectors remain ok; soft cutover is integrations ownership for hard ingress fix.

## Highest-value action this shift

**Bootstrap signal test regression after email suppression:** Email bootstrap suppression (prior shift) correctly omits `signal_watch_bootstrap_ready` when email triage items are present. Watch bootstrap/summary contract tests still expected bootstrap in the inbox but did not stub email signals — the dev `config/email-monitor-stub.json` stub produced an urgent DashPro email that suppressed bootstrap, causing 3 failures in `test_watch_bootstrap_signal` and `test_watch_summary_signal`.

### Change

- `tests/support/stable_connector_probe.py` — extend stable probe patch to stub `email_inbox_items` empty (same pattern as monitor probe stubbing)

### Receipts

- `PYTHONPATH=services/axon-watch python3 -m unittest tests.test_watch_bootstrap_signal tests.test_watch_summary_signal -v` → **7 passed**
- `python3 -m unittest tests.test_watch_bootstrap_signal tests.test_watch_summary_signal tests.test_watch_ranking tests.test_control_plane_inbox_projection tests.test_signal_consistency tests.test_parity_a4_signal_inbox_consistency -v` → **38 passed**
- `./scripts/dev/check-health.sh` → stack ok; connectors 3 ok / 1 degraded (tunnel); inbox Sentry critical unchanged

## Watch items (not acted)

- Cloudflare soft cutover (remote ingress still on `:7734`) — integrations ownership for hard cutover.
- Live DashPro Sentry critical (Google Sign-In, realtime subscribe, session init) — legitimate signal; left open for DashPro lane.
