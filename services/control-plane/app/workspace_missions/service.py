"""VAXON mission lifecycle over tasks, deliveries, and impact edges."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import threading
from typing import Any
from uuid import uuid4

from app.persistence import handoff_store, task_store, workspace_mission_store
from app.workspace_agents.teammate_route import route_teammate_decision
from app.workspace_delivery import delivery_store, get_workspace_delivery_policy, is_protected_branch
from app.workspace_missions.impact_graph import impact_edges


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
        )
    statuses = {str(node.get("status") or "") for node in nodes}
    if statuses & {"failed", "cancelled"}:
        return workspace_mission_store.update_mission(
            mission_id, status="blocked", blocker="one or more workspace tasks failed"
        )
    if mission.get("status") in {"blocked", "ready_for_promotion"}:
        return workspace_mission_store.get_mission(mission_id)
    if nodes and statuses <= {"completed"}:
        return workspace_mission_store.update_mission(
            mission_id, status="verifying", blocker=""
        )
    return workspace_mission_store.update_mission(mission_id, status="running", blocker="")


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


def _verification_commands(mission: dict[str, Any]) -> list[tuple[str, str]]:
    commands: list[tuple[str, str]] = []
    for edge in mission.get("impact") or []:
        target = str(edge.get("target_workspace_id") or "").strip()
        raw = edge.get("verification_commands")
        if isinstance(raw, list):
            commands.extend((target, str(command).strip()) for command in raw if str(command).strip())
    return commands


def verify_mission(mission_id: str) -> dict[str, Any]:
    mission = refresh_mission(mission_id)
    if mission is None:
        raise ValueError(f"mission not found: {mission_id}")
    if mission.get("status") != "verifying":
        raise ValueError(f"mission is not ready for verification ({mission.get('status')})")
    for node in mission.get("nodes") or []:
        if node.get("relation") == "impact_review":
            continue
        stage = str(node.get("delivery_stage") or "")
        if stage in {"ci_red", "blocked", "escalated"}:
            return workspace_mission_store.update_mission(
                mission_id,
                status="blocked",
                blocker=(
                    f"{node.get('workspace_id')} delivery is not green "
                    f"(stage={stage or 'missing'})"
                ),
            ) or mission
        if stage not in {"ci_green", "no_change"}:
            return workspace_mission_store.update_mission(
                mission_id,
                status="verifying",
                blocker=f"waiting for green delivery in {node.get('workspace_id')}",
            ) or mission
    commands = _verification_commands(mission)
    if len(mission.get("nodes") or []) > 1 and not commands:
        return workspace_mission_store.update_mission(
            mission_id,
            status="blocked",
            blocker="cross-workspace verification commands are not configured",
        ) or mission
    node_roots: dict[str, Path] = {}
    isolation_roots: list[Path] = []
    try:
        from app.safe_improvement.isolated_executor import cleanup_isolation_root, create_isolation_root
        from app.terminal.workspace_roots import resolve_workspace_root

        for node in mission.get("nodes") or []:
            if node.get("relation") == "impact_review":
                continue
            workspace_id = str(node.get("workspace_id") or "")
            commit = str(node.get("commit_sha") or "").strip()
            if not commit:
                return workspace_mission_store.update_mission(
                    mission_id, status="blocked",
                    blocker=f"{workspace_id} has no pinned delivery commit",
                ) or mission
            root = create_isolation_root(
                proposal_id=f"verify-{mission_id}-{workspace_id}",
                bound_project_root=resolve_workspace_root(workspace_id),
                baseline_commit=commit,
            )
            node_roots[workspace_id] = root
            isolation_roots.append(root)
        pinned_manifest = {
            "mission_id": mission_id,
            "workspaces": {
                workspace: {"commit_sha": next(
                    str(node.get("commit_sha") or "") for node in mission["nodes"]
                    if node.get("workspace_id") == workspace
                )}
                for workspace in node_roots
            },
        }
        workspace_mission_store.update_mission(mission_id, integration_manifest=pinned_manifest)
        manifest = {
            **pinned_manifest,
            "workspaces": {
                workspace: {**pinned_manifest["workspaces"][workspace], "root": str(root)}
                for workspace, root in node_roots.items()
            },
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as handle:
            json.dump(manifest, handle, sort_keys=True)
            manifest_path = handle.name
        env = dict(os.environ)
        env["AXON_MISSION_MANIFEST"] = manifest_path
        for workspace, root in node_roots.items():
            key = re.sub(r"[^A-Z0-9]+", "_", workspace.upper()).strip("_")
            env[f"AXON_MISSION_{key}_ROOT"] = str(root)
        receipts: list[dict[str, Any]] = []
        for workspace, command in commands:
            root = node_roots.get(workspace)
            if root is None:
                raise ValueError(f"verification target workspace missing: {workspace}")
            result = subprocess.run(
                command, cwd=str(root), env=env, shell=True, capture_output=True,
                text=True, timeout=900, check=False,
            )
            receipts.append({
                "workspace_id": workspace, "command": command,
                "exit_code": result.returncode,
                "output": (result.stdout or result.stderr or "")[-4000:],
            })
            if result.returncode != 0:
                return workspace_mission_store.update_mission(
                    mission_id, status="blocked",
                    blocker=f"cross-workspace verification failed in {workspace}: {command}",
                ) or mission
        for node in mission.get("nodes") or []:
            workspace_mission_store.update_node(
                str(node["node_id"]), verification={"status": "passed", "receipts": receipts}
            )
        return workspace_mission_store.update_mission(
            mission_id, status="ready_for_promotion", blocker=""
        ) or mission
    finally:
        for root in isolation_roots:
            cleanup_isolation_root(root)
        if "manifest_path" in locals():
            Path(manifest_path).unlink(missing_ok=True)


def promote_mission(mission_id: str) -> dict[str, Any]:
    mission = workspace_mission_store.get_mission(mission_id)
    if mission is None:
        raise ValueError(f"mission not found: {mission_id}")
    if mission.get("status") != "ready_for_promotion":
        raise ValueError(f"mission is not ready for promotion ({mission.get('status')})")
    if str(mission.get("risk") or "normal") not in {"low", "normal"}:
        return workspace_mission_store.update_mission(
            mission_id, blocker="operator approval required for elevated mission risk"
        ) or mission
    for node in mission.get("nodes") or []:
        if node.get("relation") == "impact_review":
            continue
        workspace = str(node.get("workspace_id") or "")
        policy = get_workspace_delivery_policy(workspace)
        if policy is None or is_protected_branch(policy, policy.base_branch):
            _record_promotion(mission_id, node, "approval_required", "protected integration branch")
            return workspace_mission_store.update_mission(
                mission_id,
                blocker=f"operator approval required for protected promotion in {workspace}",
            ) or mission
        pr_url = str(node.get("draft_pr_url") or "").strip()
        if str(node.get("delivery_stage") or "") == "no_change":
            _record_promotion(mission_id, node, "no_change", "nothing to promote")
            continue
        if not pr_url:
            raise ValueError(f"mission node has no draft PR: {workspace}")
        ready = subprocess.run(
            ["gh", "pr", "ready", pr_url],
            capture_output=True, text=True, timeout=120, check=False,
        )
        if ready.returncode != 0 and "already marked ready" not in (
            ready.stderr or ready.stdout
        ).lower():
            _record_promotion(mission_id, node, "failed", (ready.stderr or ready.stdout).strip())
            return workspace_mission_store.update_mission(
                mission_id, status="blocked",
                blocker=f"could not mark draft PR ready in {workspace}: "
                f"{(ready.stderr or ready.stdout).strip()}",
            ) or mission
        result = subprocess.run(
            ["gh", "pr", "merge", pr_url, "--merge", "--delete-branch"],
            capture_output=True, text=True, timeout=120, check=False,
        )
        if result.returncode != 0:
            _record_promotion(mission_id, node, "failed", (result.stderr or result.stdout).strip())
            return workspace_mission_store.update_mission(
                mission_id, status="blocked",
                blocker=f"promotion failed in {workspace}: {(result.stderr or result.stdout).strip()}",
            ) or mission
        _record_promotion(mission_id, node, "promoted", pr_url)
    return workspace_mission_store.update_mission(
        mission_id, status="completed", blocker=""
    ) or mission


def _record_promotion(
    mission_id: str, node: dict[str, Any], status: str, detail: str
) -> None:
    mission = workspace_mission_store.get_mission(mission_id) or {}
    records = list(mission.get("promotions") or [])
    record = {
        "node_id": node.get("node_id"),
        "workspace_id": node.get("workspace_id"),
        "commit_sha": node.get("commit_sha"),
        "draft_pr_url": node.get("draft_pr_url"),
        "status": status,
        "detail": detail,
    }
    records = [item for item in records if item.get("node_id") != node.get("node_id")]
    records.append(record)
    workspace_mission_store.update_mission(mission_id, promotions=records)


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
        mission_id, status="running", blocker=""
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
        mission_id, status="cancelled", blocker="cancelled by operator"
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
                    )

    threading.Thread(target=_work, daemon=True, name=f"mission-{task_id[:12]}").start()


__all__ = [
    "auto_create_mission_for_task", "cancel_mission", "create_workspace_mission", "get_workspace_mission",
    "kick_missions_for_task", "list_workspace_missions", "preview_workspace_impact",
    "promote_mission", "refresh_mission", "retry_mission", "verify_mission",
]
