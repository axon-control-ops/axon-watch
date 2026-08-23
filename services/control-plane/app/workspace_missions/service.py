"""VAXON mission lifecycle over tasks, deliveries, and impact edges."""

from __future__ import annotations

import hashlib
import os
import threading
from typing import Any
from uuid import uuid4

from app.persistence import handoff_store, task_store, workspace_mission_store
from app.workspace_agents.teammate_route import route_teammate_decision
from app.workspace_delivery import delivery_store
from app.workspace_missions.impact_graph import impact_edges
from app.workspace_missions.verification import promote_mission, verify_mission


def _enabled() -> bool:
    raw = os.environ.get("AXON_CROSS_WORKSPACE_MISSIONS", "1")
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _auto_promote_enabled() -> bool:
    raw = os.environ.get("AXON_MISSION_AUTO_PROMOTE", "0")
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _dedupe(source: str, goal: str, change_identity: str = "") -> str:
    normalized = " ".join(goal.lower().split())
    digest = hashlib.sha256(
        f"{source}\0{normalized}\0{change_identity.strip()}".encode()
    ).hexdigest()[:20]
    return f"mission:{source}:{digest}"


def _route_role(workspace_id: str, goal: str) -> str:
    try:
        decision = route_teammate_decision(
            workspace_id=workspace_id, prompt=goal, use_model_tiebreak=False
        )
        if decision.should_route and decision.employee is not None:
            return str(decision.employee.role or "lead").strip().lower() or "lead"
    except Exception:
        pass
    return "lead"


def preview_workspace_impact(
    source_workspace_id: str, goal: str = "", changed_paths: list[str] | None = None
) -> dict[str, Any]:
    edges = impact_edges(source_workspace_id, changed_paths=changed_paths)
    actionable = [edge for edge in edges if edge.get("actionable")]
    review = [edge for edge in edges if not edge.get("actionable")]
    return {
        "source_workspace_id": source_workspace_id,
        "goal": goal,
        "changed_paths": list(changed_paths or []),
        "edges": edges,
        "actionable_count": len(actionable),
        "review_count": len(review),
    }


def create_workspace_mission(
    *,
    source_workspace_id: str,
    goal: str,
    risk: str = "normal",
    source_task_id: str | None = None,
    source_run_id: str | None = None,
    changed_paths: list[str] | None = None,
) -> dict[str, Any]:
    if not _enabled():
        raise ValueError("cross-workspace missions are disabled")
    source = source_workspace_id.strip()
    objective = goal.strip()
    if not source or not objective:
        raise ValueError("source_workspace_id and goal are required")
    dedupe_key = _dedupe(source, objective, source_run_id or source_task_id or "")
    existing = workspace_mission_store.get_by_dedupe_key(dedupe_key)
    if existing:
        return existing
    preview = preview_workspace_impact(source, objective, changed_paths)
    mission_id = f"mission-{uuid4().hex[:16]}"
    mission = workspace_mission_store.create_mission(
        {
            "mission_id": mission_id,
            "dedupe_key": dedupe_key,
            "goal": objective,
            "status": "planned",
            "risk": risk,
            "source_workspace_id": source,
            "source_task_id": source_task_id,
            "source_run_id": source_run_id,
            "impact": preview["edges"],
        }
    )
    source_task = task_store.get_task(source_task_id) if source_task_id else None
    if source_task is None:
        source_role = _route_role(source, objective)
        source_task = task_store.create_task(
            workspace_id=source,
            goal=objective,
            acceptance_criteria=(
                f"Deliver the source slice for cross-workspace mission {mission_id}; "
                "publish verified receipts before consumers start."
            ),
            risk=risk,
            owner_role=source_role,
            mission_id=mission_id,
        )
    source_task_key = str(source_task["task_id"])
    workspace_mission_store.update_mission(mission_id, source_task_id=source_task_key)
    workspace_mission_store.attach_task_mission(source_task_key, mission_id)
    workspace_mission_store.create_node(
        {
            "node_id": f"mnode-{uuid4().hex[:16]}",
            "mission_id": mission_id,
            "workspace_id": source,
            "task_id": source_task_key,
            "owner_role": str(source_task.get("owner_role") or "lead"),
            "relation": "source",
            "status": str(source_task.get("status") or "open"),
            "promotion_order": 0,
        }
    )
    for index, edge in enumerate(preview["edges"], start=1):
        target = str(edge.get("target_workspace_id") or "").strip()
        if not target:
            continue
        actionable = bool(edge.get("actionable"))
        target_goal = (
            f"Update {target} for cross-workspace mission {mission_id}: {objective}"
            if actionable
            else f"Review possible cross-workspace impact from {source}: {objective}"
        )
        role = _route_role(target, target_goal) if actionable else "lead"
        dependencies = [source_task_key] if actionable else []
        task = task_store.create_task(
            workspace_id=target,
            goal=target_goal,
            acceptance_criteria=(
                f"Mission {mission_id}. Verify compatibility with {source}; include contract and "
                "integration receipts."
            ),
            risk=risk if actionable else "high",
            owner_role=role,
            dependencies=dependencies,
            mission_id=mission_id,
        )
        handoff = handoff_store.create_handoff_record(
            source_workspace_id=source,
            target_workspace_id=target,
            task=target_goal,
            reason=f"Cross-workspace mission {mission_id}",
            mission_id=mission_id,
        )
        handoff_store.update_handoff(
            str(handoff["handoff_id"]),
            status="routed" if actionable else "needs_review",
            target_task_id=str(task["task_id"]),
            routed_role=role,
        )
        workspace_mission_store.create_node(
            {
                "node_id": f"mnode-{uuid4().hex[:16]}",
                "mission_id": mission_id,
                "workspace_id": target,
                "task_id": task["task_id"],
                "owner_role": role,
                "relation": "affected" if actionable else "impact_review",
                "status": "open",
                "dependency_task_ids": dependencies,
                "promotion_order": int(edge.get("promotion_order") or index),
                "blocker": "" if actionable else str(edge.get("review_reason") or "impact review required"),
            }
        )
    status = "blocked" if preview["review_count"] else "running"
    blocker = "ambiguous workspace impact requires Lead review" if preview["review_count"] else ""
    workspace_mission_store.update_mission(mission_id, status=status, blocker=blocker)
    if status == "running":
        try:
            _start_ready_nodes(workspace_mission_store.get_mission(mission_id) or {})
        except Exception:
            pass
    return get_workspace_mission(mission_id) or mission


def auto_create_mission_for_task(task_id: str) -> dict[str, Any] | None:
    """Full Auto leases become missions only when the impact graph has evidence."""
    if not _enabled():
        return None
    from app.persistence import operator_presence_settings_store

    if operator_presence_settings_store.load_settings().get("autonomy_mode") != "full":
        return None
    task = task_store.get_task(task_id)
    if task is None or task.get("mission_id"):
        return None
    preview = preview_workspace_impact(str(task["workspace_id"]), str(task["goal"]))
    if not preview["edges"]:
        return None
    return create_workspace_mission(
        source_workspace_id=str(task["workspace_id"]),
        goal=str(task["goal"]),
        risk=str(task.get("risk") or "normal"),
        source_task_id=task_id,
        source_run_id=str(task.get("run_id") or "") or None,
    )


def _sync_node(node: dict[str, Any]) -> dict[str, Any]:
    task = task_store.get_task(str(node.get("task_id") or ""))
    fields: dict[str, Any] = {}
    if task is not None:
        fields["status"] = str(task.get("status") or "planned")
        run_id = str(task.get("run_id") or "").strip()
        delivery = delivery_store.get_delivery_by_run(run_id) if run_id else None
        if delivery:
            fields.update(
                delivery_id=delivery.get("delivery_id"),
                commit_sha=delivery.get("commit_sha") or delivery.get("baseline_sha"),
                draft_pr_url=delivery.get("draft_pr_url"),
                delivery_stage=delivery.get("stage"),
            )
    return workspace_mission_store.update_node(str(node["node_id"]), **fields) or node


def refresh_mission(mission_id: str) -> dict[str, Any] | None:
    mission = workspace_mission_store.get_mission(mission_id)
    if mission is None or mission.get("status") in {"completed", "cancelled"}:
        return mission
    nodes = [_sync_node(node) for node in mission.get("nodes") or []]
    pending_reviews = [
        node for node in nodes
        if node.get("relation") == "impact_review" and node.get("status") != "completed"
    ]
    if pending_reviews:
        return workspace_mission_store.update_mission(
            mission_id,
            status="blocked",
            blocker="ambiguous workspace impact requires Lead review",
            blocker_code="impact_review",
        )
    statuses = {str(node.get("status") or "") for node in nodes}
    if statuses & {"failed", "cancelled"}:
        return workspace_mission_store.update_mission(
            mission_id, status="blocked", blocker="one or more workspace tasks failed",
            blocker_code="task_failed",
        )
    if mission.get("status") == "ready_for_promotion":
        return workspace_mission_store.get_mission(mission_id)
    if mission.get("status") == "blocked" and str(mission.get("blocker_code") or "") not in {
        "delivery_gate", "impact_review", "task_failed",
    }:
        return workspace_mission_store.get_mission(mission_id)
    if nodes and statuses <= {"completed"}:
        return workspace_mission_store.update_mission(
            mission_id, status="verifying", blocker="", blocker_code=""
        )
    return workspace_mission_store.update_mission(
        mission_id, status="running", blocker="", blocker_code=""
    )


def _dependencies_complete(node: dict[str, Any]) -> bool:
    for dependency_id in node.get("dependency_task_ids") or []:
        dependency = task_store.get_task(str(dependency_id))
        if dependency is None or dependency.get("status") != "completed":
            return False
    return True


def _start_ready_nodes(mission: dict[str, Any]) -> None:
    from app.workspace_handoff_routing import try_autostart_handoff_task

    for node in mission.get("nodes") or []:
        task = task_store.get_task(str(node.get("task_id") or ""))
        if task and task.get("status") == "open" and _dependencies_complete(node):
            try_autostart_handoff_task(str(task["task_id"]))


def get_workspace_mission(mission_id: str) -> dict[str, Any] | None:
    return refresh_mission(mission_id)


def list_workspace_missions(*, status: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    for mission in workspace_mission_store.list_missions(status=status, limit=limit):
        refresh_mission(str(mission["mission_id"]))
    return workspace_mission_store.list_missions(status=status, limit=limit)


def retry_mission(mission_id: str) -> dict[str, Any]:
    mission = workspace_mission_store.get_mission(mission_id)
    if mission is None:
        raise ValueError(f"mission not found: {mission_id}")
    for node in mission.get("nodes") or []:
        task = task_store.get_task(str(node.get("task_id") or ""))
        if not task or task.get("status") != "failed":
            continue
        verification = dict(node.get("verification") or {})
        repair_count = int(verification.get("repair_count") or 0)
        if repair_count >= 2:
            continue
        repair = task_store.create_task(
            workspace_id=str(node["workspace_id"]),
            goal=f"Repair mission {mission_id} after failed task {task['task_id']}: {mission['goal']}",
            acceptance_criteria="Resolve the bounded failure and publish green verification receipts.",
            risk=str(mission.get("risk") or "normal"),
            owner_role=str(node.get("owner_role") or "lead"),
            dependencies=list(node.get("dependency_task_ids") or []),
            mission_id=mission_id,
            attempt_budget=2,
        )
        verification["repair_count"] = repair_count + 1
        workspace_mission_store.update_node(
            str(node["node_id"]), task_id=str(repair["task_id"]),
            status="open", blocker="", verification=verification,
        )
    updated = workspace_mission_store.update_mission(
        mission_id, status="running", blocker="", blocker_code=""
    ) or mission
    _start_ready_nodes(updated)
    return updated


def cancel_mission(mission_id: str) -> dict[str, Any]:
    mission = workspace_mission_store.get_mission(mission_id)
    if mission is None:
        raise ValueError(f"mission not found: {mission_id}")
    for node in mission.get("nodes") or []:
        task = task_store.get_task(str(node.get("task_id") or ""))
        if task and task.get("status") == "open":
            try:
                task_store.cancel_task(str(task["task_id"]), terminal_outcome="mission_cancelled")
            except Exception:
                pass
    return workspace_mission_store.update_mission(
        mission_id, status="cancelled", blocker="cancelled by operator",
        blocker_code="operator_cancelled",
    ) or mission


def kick_missions_for_task(task_id: str) -> None:
    """Refresh/verify related missions after a task reaches a terminal state."""
    def _work() -> None:
        for mission in workspace_mission_store.list_missions(limit=200):
            if not any(str(node.get("task_id") or "") == task_id for node in mission.get("nodes") or []):
                continue
            refreshed = refresh_mission(str(mission["mission_id"]))
            failed_task = task_store.get_task(task_id)
            if (
                refreshed and refreshed.get("status") == "blocked"
                and failed_task and failed_task.get("status") == "failed"
            ):
                refreshed = retry_mission(str(mission["mission_id"]))
            if refreshed and refreshed.get("status") == "running":
                _start_ready_nodes(refreshed)
            if refreshed and refreshed.get("status") == "verifying":
                try:
                    verified = verify_mission(str(mission["mission_id"]))
                    if verified.get("status") == "ready_for_promotion" and _auto_promote_enabled():
                        promote_mission(str(mission["mission_id"]))
                except Exception as exc:
                    workspace_mission_store.update_mission(
                        str(mission["mission_id"]), status="blocked",
                        blocker=f"mission verification error: {exc}",
                        blocker_code="verification_error",
                    )

    threading.Thread(target=_work, daemon=True, name=f"mission-{task_id[:12]}").start()


__all__ = [
    "auto_create_mission_for_task", "cancel_mission", "create_workspace_mission", "get_workspace_mission",
    "kick_missions_for_task", "list_workspace_missions", "preview_workspace_impact",
    "promote_mission", "refresh_mission", "retry_mission", "verify_mission",
]
