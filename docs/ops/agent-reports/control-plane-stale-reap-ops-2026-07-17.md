# Control Plane digest — 2026-07-17 (ops follow-up)

Role: Control Plane (APIs, runs, approvals, persistence)  
Workspace: workspace_axon_watch  
Shift: continuous

## Highest-value action this shift

**Harden stale worker-run recovery:** the reaper shipped earlier today; this shift adds startup + manual triggers so hung role-tagged shifts clear without waiting for the first scheduler tick.

### Change

- `services/control-plane/app/bootstrap.py` — call `reap_stale_employee_runs()` on startup when the worker scheduler is enabled
- `services/control-plane/app/routes/runs.py` — `POST /api/runs/reconcile-stale` for on-demand stale fail (returns reaped run ids + TTL)
- `tests/test_run_stale_reconcile.py` — approval-wait exemption test + API endpoint test

### Live observation (before restart)

| Check | Result |
|---|---|
| Control plane health | ok (`boot_id=ae62cfc07c5c4508adc7c6f7a51f2111`) |
| Total runs | 201 |
| Employee `executing` | 8 (axon-watch + DashPro continuous shifts; all fresh, none past 720s TTL) |
| Stale employee runs | 0 |

Active employee shifts are expected during continuous scheduling. The running process started at 07:05; latest stale-reconcile edits landed after that boot — **restart control-plane** to load the new bootstrap route and reaper module into memory.

### Post-restart verification (07:37+; no second restart)

| Check | Result |
|---|---|
| Control plane health | ok (`boot_id=97f4983110454d2a9a65836608852cb8`, pid `1356567`) |
| Staffing config path | resolves `config/workspace-agents.json`; companies `workspace_axon_watch`, `workspace_dashpro` |
| Continuous tick | starts 0 new runs (all continuous/always-on slots already filled) |
| Role-tagged `executing` | 8 (4 Axon-X + 4 DashPro: backend/frontend/integrations/watcher) |
| `POST /api/runs/reconcile-stale` | `{ count: 0, stale_seconds: 720.0 }` |
| Stack health | console / control-plane / watch all ok |

### Receipts

- `python3 -m unittest tests.test_run_stale_reconcile tests.test_workspace_agent_scheduler tests.test_control_plane_runs tests.test_run_startup_reconcile -v` → **39 passed**
- `./scripts/dev/check-health.sh` → green after restart
- Manual stale reconcile exercised live after restart (zero reaped)

### Notes

- Untagged interactive runs and approval waits are never auto-failed.
- Manual trigger after restart: `curl -X POST http://127.0.0.1:8787/api/runs/reconcile-stale`
- TTL knob: `AXON_WATCH_WORKER_RUN_STALE_SECONDS` (default 720)
- Staffing path fix (`parents[4]` repo root) is loaded in the current control-plane process; do not restart again unless code changes.
