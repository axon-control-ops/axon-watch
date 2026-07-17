# Control Plane digest — 2026-07-17

Role: Control Plane (APIs, runs, approvals, persistence)  
Workspace: workspace_axon_watch  
Shift: continuous

## Highest-value action this shift

**Run lifecycle fix:** role-tagged continuous worker shifts could stay in `executing` after a hung dispatch, blocking the next shift for that role (active-role gate + executing debt bound).

### Change

- `services/control-plane/app/runs/stale_reconcile.py` — fail employee-role `executing` runs older than wall-clock TTL (default 720s; `AXON_WATCH_WORKER_RUN_STALE_SECONDS`)
- `services/control-plane/app/workspace_agents/scheduler.py` — reap stale runs at the start of each continuous worker tick
- `services/control-plane/app/runs/service.py` — export reaper helpers
- `.env.example` — document scheduler / stale TTL knobs
- `tests/test_run_stale_reconcile.py` — coverage for stale fail, fresh keep, untagged keep, tick wiring

### Receipts

- Live observation before fix: 8 role-tagged runs stuck in `executing` (worker shifts across axon-watch + DashPro)
- `python3 -m unittest tests.test_run_stale_reconcile tests.test_workspace_agent_scheduler tests.test_control_plane_runs tests.test_run_startup_reconcile -v` → **36 passed**

### Notes

- Untagged interactive runs are never auto-failed.
- Approval waits are not auto-failed.
- `AXON_WATCH_WORKER_RUN_STALE_SECONDS` is honored on scheduler ticks (default 720s).
- Process restart is required for the running control-plane to load this code.
