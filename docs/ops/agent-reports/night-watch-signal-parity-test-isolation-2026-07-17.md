# Night Watch digest — 2026-07-17 (signal parity test isolation)

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
| Inbox | 1 item — DashPro Sentry critical (legitimate child-project signal) |

## Highest-value action this shift

**Signal parity test isolation bug:** P-A4 cross-surface parity tests (`inbox`, runtime summary,
briefing) were leaking the **live** watch inbox instead of mocked fixtures. `setUp()` cleared
cached `app.*` modules but `TestClient` still bound to a stale FastAPI app whose route handlers
pointed at deleted modules — so `fetch_watch_inbox` mocks never applied and tests failed whenever
the live stack had a Sentry critical (or passed/flaked depending on load order).

### Change

- `tests/support/control_plane_app_loader.py` — add `load_control_plane_app()` helper that
  re-imports a fresh app after module cache clear
- `tests/test_parity_a4_signal_inbox_consistency.py` — use fresh app in `setUp`
- `tests/test_signal_consistency.py` — use fresh app in `setUp`
- `tests/test_control_plane_inbox_projection.py` — single prepare + co-located imports so
  exception types and route handlers stay on the same module objects

### Receipts

- `python3 -m unittest tests.test_parity_a4_signal_inbox_consistency tests.test_signal_consistency tests.test_control_plane_inbox_projection -v` → **18 passed**
- `./scripts/dev/check-health.sh` → stack ok, 4 connectors ok, live Sentry critical unchanged

## Watch items (not acted)

- Cloudflare soft cutover (remote ingress still on `:7734`) — integrations ownership for hard cutover.
- Live DashPro Sentry critical (Google Sign-In, realtime subscribe, session init) — legitimate signal; left open for DashPro lane.
