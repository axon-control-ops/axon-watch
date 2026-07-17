# Bridge digest — 2026-07-17 (tunnel startup autostart gate)

Role: integrations (connectors, watch service, cross-repo wiring)  
Workspace: workspace_axon_watch  
Shift: continuous

## Highest-value action this shift

**Tunnel startup autostart regression gate:** watch now calls `attempt_tunnel_autostart`
after vault auto-unlock on startup, but the helper shipped without unit tests or
documented env override. A failed autostart must never block readiness.

### Change

- `tests/test_tunnel_remote_control.py` — `TunnelAutostartTests` (7 cases: env
  toggle, slice-off skip, success path, control-error swallow, unexpected-error swallow)
- `.env.example` — `AXON_WATCH_TUNNEL_AUTOSTART` documented
- `docs/NATIVE_TUNNEL_CONTROL.md` — startup autostart section + verification note
- `scripts/verify/test3-watch-connectors.sh` — drop duplicate un-isolated
  `test_connector_probe_cache` run (keep PYTHONPATH-isolated pass only)

### Receipts

- `PYTHONPATH=services/axon-watch python3 -m unittest tests.test_tunnel_remote_control.TunnelAutostartTests -v` → **7 passed**
- `PYTHONPATH=services/axon-watch python3 -m unittest tests.test_tunnel_remote_control -v` → full module ok

### Not acted (deferred)

- Cloudflare **hard cutover** (remote ingress still on `:7734`) — requires Cloudflare
  remote config change outside repo; watch continues soft cutover observation via
  `tunnel_probe.py`.
