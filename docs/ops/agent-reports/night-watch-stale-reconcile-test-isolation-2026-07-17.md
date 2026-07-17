# Night Watch digest — 2026-07-17 (stale reconcile test isolation)

Role: watcher (signals, connectors, runtime health)  
Workspace: workspace_axon_watch  
Shift: always_on

## Runtime health (live)

| Check | Result |
|---|---|
| Console web `:4173` | ok |
| Control plane health/ready | ok / ready |
| Watch health/ready (`:8788`) | ok / ready |
| Connectors | 4 configured, 3 ok, 1 degraded, 0 required unavailable |
| Runtime degraded | inactive |
| Inbox | 1 item — DashPro Sentry critical (legitimate child-project signal) |

Connector notes:

- Cloudflare tunnel is **degraded** (process up; public health still hits axon-local on `:7734`). Required connectors remain ok; soft cutover is integrations ownership for hard ingress fix.

## Highest-value action this shift

**Runtime health test isolation bug:** Watch-side tests (`test_dashpro_sentry`, `test_monitor_inbox_integration`, etc.) wipe cached `app.*` modules to isolate axon-watch imports. When the stale employee-run reconcile suite ran afterward in the same interpreter, `run_continuous_worker_tick` still pointed at a stale scheduler module — scheduler config mocks were ignored and the tick started six real continuous shifts instead of reaping the seeded stale run.

### Change

- `tests/test_run_stale_reconcile.py` — re-import control-plane modules in `setUp` via `prepare_control_plane_imports()` (same pattern as P-A4 parity tests); bind API test to `load_control_plane_app()` for a fresh FastAPI app

### Receipts

- `python3 -m unittest tests.test_connector_signal tests.test_connector_inbox_integration tests.test_monitor_inbox_integration tests.test_dashpro_sentry tests.test_parity_a4_signal_inbox_consistency tests.test_run_stale_reconcile -v` → **39 passed**
- `./scripts/dev/check-health.sh` → stack ok; connectors 3 ok / 1 degraded (tunnel); inbox Sentry critical unchanged

## Watch items (not acted)

- Cloudflare soft cutover (remote ingress still on `:7734`) — integrations ownership for hard cutover.
- Live DashPro Sentry critical (Google Sign-In, realtime subscribe, session init) — legitimate signal; left open for DashPro lane.
