# Workspace Handoff Slice

## Purpose

Parity requires one verified cross-workspace handoff from operator request to
target workspace summary. This slice persists the handoff record, returns the
target workspace catalog + run summary, and best-effort **routes a ticket** into
the target workspace ledger with team communication.

Opening the target workspace in the shell is still useful for live observation.
The durable work unit is created on the target when routing succeeds; agent
execution still starts via workers / operator follow-through.

## Automatic routing (default)

On `POST .../handoffs` the control-plane best-effort:

1. Records the handoff (`status` starts as `recorded`)
2. Creates a Gate 4 `workspace_tasks` row on the **target** workspace
3. Specialty-routes an owner on the target roster (falls back to Lead)
4. Posts IDE-thread messages on the target owner thread and a Lead ack on source
5. Updates the handoff to `status: routed` with `target_task_id`, `routed_role`,
   and communication thread ids when ticket create succeeds

This creates a durable target ticket and chat notice. It does **not** auto-start
an agent run; continuous workers / operator Retry still pick up leased work.

If ticket create fails, the handoff remains `recorded` (POST still returns 200
with the audit record).

VAXON Advise (SA-2) ranks open handoffs with incomplete follow-through above
degraded-runtime facts.

## API

### Create handoff

`POST /api/workspaces/{source_workspace_id}/handoffs`

Request:

```json
{
  "target_workspace_id": "workspace_axon_local",
  "task": "Review axon-local after connection slice",
  "reason": "Cross-repo follow-up"
}
```

Response:

```json
{
  "handoff": {
    "handoff_id": "handoff-…",
    "source_workspace_id": "workspace_smoke",
    "target_workspace_id": "workspace_axon_local",
    "task": "…",
    "reason": "…",
    "status": "routed",
    "target_task_id": "task-…",
    "routed_role": "backend",
    "routed_employee_id": "…",
    "communication_thread_id": "thread_…",
    "source_communication_thread_id": "thread_…",
    "created_at": "…",
    "updated_at": "…"
  },
  "target_task_id": "task-…",
  "routed_role": "backend",
  "communication_thread_id": "thread_…",
  "target_workspace": { "workspace_id": "…", "connection_kind": "…" },
  "target_workspace_summary": {
    "workspace_id": "…",
    "connection_kind": "…",
    "project_root": "…",
    "run_count": 0,
    "active_run_count": 0,
    "active_runs": []
  }
}
```

### List handoffs for a workspace

`GET /api/workspaces/{workspace_id}/handoffs`

Returns handoffs where the workspace is source or target, newest first.

## Persistence

SQLite table `workspace_handoffs` in the control-plane database schema
(`services/control-plane/app/persistence/run_store_sqlite.py`).

Store module: `services/control-plane/app/persistence/handoff_store.py`

Orchestration: `services/control-plane/app/workspace_handoffs.py`

Routing + communication: `services/control-plane/app/workspace_handoff_routing.py`

Shared DTOs: `packages/shared-types/src/control-plane.ts`
(`WorkspaceHandoffRecord`, `WorkspaceHandoffSummary` fields on summary payload).

## Verification

Unit/API:

```bash
python3 -m unittest tests.test_control_plane_workspace_handoffs -v
python3 -m unittest tests.test_operator_fleet_advice -v
```

Live acceptance:

```bash
./scripts/verify/test2-workspace-handoff.sh
npm run verify:test2
```

Live proof:

1. `POST` handoff from `workspace_smoke` → `workspace_axon_local`
2. Response includes `handoff_id`, `status: routed`, `target_task_id`, and target
   summary with `project_root` ending in `axon-local`
3. `GET /api/workspaces/workspace_smoke/handoffs` lists the same record
4. Target workspace task board shows the routed ticket / handoff strip

Restart control-plane after route changes. TEST-2 restarts control-plane when the
dev stack is already running.

## Cutover status

Locked cutover item **Workspace handoff slice** — verified by TEST-2; routing
extension keeps the same POST contract and adds ticket follow-through.

Next locked item: **Watch command / event / status depth**.
