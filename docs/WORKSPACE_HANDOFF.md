# Workspace Handoff Slice

## Purpose

Parity requires one verified cross-workspace handoff from operator request to
target workspace summary. This slice adds an explicit, persisted handoff record
and returns the target workspace catalog + run summary in the same response.

Manual follow-through (opening the target workspace in the shell) remains
operator-driven; the handoff record is the durable audit trail.

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
    "status": "recorded",
    "created_at": "…",
    "updated_at": "…"
  },
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

Shared DTOs: `packages/shared-types/src/control-plane.ts`
(`WorkspaceHandoffRecord`, `WorkspaceHandoffSummary` fields on summary payload).

## Verification

Unit/API:

```bash
python3 -m unittest tests.test_control_plane_workspace_handoffs -v
```

Live acceptance:

```bash
./scripts/verify/test2-workspace-handoff.sh
npm run verify:test2
```

Live proof:

1. `POST` handoff from `workspace_smoke` → `workspace_axon_local`
2. Response includes `handoff_id`, `status: recorded`, and target summary with
   `project_root` ending in `axon-local`
3. `GET /api/workspaces/workspace_smoke/handoffs` lists the same record

Restart control-plane after route changes. TEST-2 restarts control-plane when the
dev stack is already running.

## Cutover status

Locked cutover item **Workspace handoff slice** — verified by TEST-2.

Next locked item: **Watch command / event / status depth**.
