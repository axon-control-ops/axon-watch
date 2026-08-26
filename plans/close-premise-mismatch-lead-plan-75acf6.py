#!/usr/bin/env python3
"""Close lead-plan-75acf6b60b6143e8 (premise mismatch) and finalize linked task."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CP_ROOT = REPO_ROOT / "services" / "control-plane"
sys.path.insert(0, str(CP_ROOT))

PLAN_ID = "lead-plan-75acf6b60b6143e8"
TASK_ID = "task-622f221addeb4873"
WORKSPACE_ID = "workspace_axon_watch"
TERMINAL_OUTCOME = (
    "premise mismatch: Axon-X uses Tauri/Vue → control-plane (SQLite), not Electron→Supabase; "
    "live Supabase data belongs on workspace_dashpro"
)


def _load_dotenv() -> None:
    env_file = REPO_ROOT / ".env"
    if not env_file.is_file():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _backfill_completed_task(*, goal: str, acceptance_criteria: str) -> dict[str, object]:
    from datetime import datetime, timezone

    from app.persistence import run_store_sqlite, task_store

    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    connection = run_store_sqlite.connect(os.environ.get("AXON_WATCH_CONTROL_PLANE_DB"))
    try:
        task_store.ensure_task_ledger_schema(connection)
        connection.execute(
            """
            INSERT INTO workspace_tasks (
                task_id, workspace_id, goal, acceptance_criteria, risk, owner_role,
                dependencies_json, exclusive_paths_json, allowed_paths_json,
                approval_receipt_id, mission_id, status, lease_holder, lease_expires_at,
                attempt_budget, attempts_used, terminal_outcome, run_id, created_at, updated_at
            ) VALUES (?, ?, ?, ?, 'normal', 'backend', '[]', '["docs/ops/agent-reports/"]',
                      '["docs/ops/agent-reports/"]', NULL, NULL, 'completed', NULL, NULL,
                      3, 1, ?, NULL, ?, ?)
            """,
            (TASK_ID, WORKSPACE_ID, goal, acceptance_criteria, TERMINAL_OUTCOME, now, now),
        )
        connection.commit()
    finally:
        connection.close()
    stored = task_store.get_task(TASK_ID)
    if stored is None:
        raise RuntimeError(f"failed to backfill task {TASK_ID}")
    return {"action": "backfilled_completed", "status": stored.get("status"), "terminal_outcome": stored.get("terminal_outcome")}


def main() -> int:
    _load_dotenv()

    from app.persistence import task_store
    from app.workspace_agents import lead_plan_store

    plan = lead_plan_store.get_plan(PLAN_ID)
    if plan is None:
        print(json.dumps({"error": f"plan not found: {PLAN_ID}"}))
        return 1

    plan_json = plan.get("plan") if isinstance(plan.get("plan"), dict) else {}
    items = plan_json.get("items") if isinstance(plan_json.get("items"), list) else []
    backend_item = next(
        (item for item in items if isinstance(item, dict) and item.get("plan_key") == "plan-01-backend"),
        {},
    )
    goal = str(backend_item.get("goal") or plan.get("goal") or "").strip()
    acceptance = str(backend_item.get("acceptance_criteria") or "").strip()

    task_result: dict[str, object] = {"task_id": TASK_ID}
    task = task_store.get_task(TASK_ID)
    if task is None:
        task_result.update(_backfill_completed_task(goal=goal, acceptance_criteria=acceptance))
    elif task.get("status") == "completed":
        task_result.update(
            {
                "action": "already_completed",
                "status": task.get("status"),
                "terminal_outcome": task.get("terminal_outcome"),
            }
        )
    elif task.get("status") in {"cancelled", "failed"}:
        task_result.update(
            {
                "action": "already_terminal",
                "status": task.get("status"),
                "terminal_outcome": task.get("terminal_outcome"),
            }
        )
    else:
        completed = task_store.complete_task(TASK_ID, terminal_outcome=TERMINAL_OUTCOME)
        task_result.update(
            {
                "action": "completed",
                "status": completed.get("status"),
                "terminal_outcome": completed.get("terminal_outcome"),
            }
        )

    lead_plan_store.append_receipt(
        plan_id=PLAN_ID,
        workspace_id=WORKSPACE_ID,
        kind="premise_mismatch_closed",
        payload={
            "summary": TERMINAL_OUTCOME,
            "actor": "lead",
            "task_id": TASK_ID,
            "task_result": task_result,
            "receipt_path": "tests/receipts/backend-lead-plan-75acf6b6143e8-validation-2026-08-25.md",
            "routing_note": "If live Supabase product data was required, route to workspace_dashpro (DashPro).",
        },
    )

    updated_plan = lead_plan_store.set_plan_status(PLAN_ID, "cancelled")

    print(
        json.dumps(
            {
                "plan_id": PLAN_ID,
                "plan_status": updated_plan.get("status"),
                "task": task_result,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
