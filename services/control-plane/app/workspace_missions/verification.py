"""Pinned-revision verification and promotion for cross-workspace missions."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Any

from app.persistence import workspace_mission_store
from app.workspace_delivery import get_workspace_delivery_policy, is_protected_branch


def _verification_commands(mission: dict[str, Any]) -> list[tuple[str, str]]:
    commands: list[tuple[str, str]] = []
    for edge in mission.get("impact") or []:
        target = str(edge.get("target_workspace_id") or "").strip()
        raw = edge.get("verification_commands")
        if isinstance(raw, list):
            commands.extend((target, str(command).strip()) for command in raw if str(command).strip())
    return commands


def _green_delivery_gate(mission_id: str, mission: dict[str, Any]) -> dict[str, Any] | None:
    for node in mission.get("nodes") or []:
        if node.get("relation") == "impact_review":
            continue
        stage = str(node.get("delivery_stage") or "")
        if stage in {"ci_red", "blocked", "escalated"}:
            return workspace_mission_store.update_mission(
                mission_id, status="blocked",
                blocker=f"{node.get('workspace_id')} delivery is not green (stage={stage})",
                blocker_code="delivery_gate",
            )
        if stage not in {"ci_green", "no_change"}:
            return workspace_mission_store.update_mission(
                mission_id, status="verifying",
                blocker=f"waiting for green delivery in {node.get('workspace_id')}",
            )
    return None


def _materialize_pinned_roots(
    mission_id: str, mission: dict[str, Any]
) -> tuple[dict[str, Path], list[Path]]:
    from app.safe_improvement.isolated_executor import create_isolation_root
    from app.terminal.workspace_roots import resolve_workspace_root

    roots: dict[str, Path] = {}
    for node in mission.get("nodes") or []:
        if node.get("relation") == "impact_review":
            continue
        workspace_id = str(node.get("workspace_id") or "")
        commit = str(node.get("commit_sha") or "").strip()
        if not commit:
            raise ValueError(f"{workspace_id} has no pinned delivery commit")
        roots[workspace_id] = create_isolation_root(
            proposal_id=f"verify-{mission_id}-{workspace_id}",
            bound_project_root=resolve_workspace_root(workspace_id),
            baseline_commit=commit,
        )
    return roots, list(roots.values())


def _manifests(
    mission_id: str, mission: dict[str, Any], roots: dict[str, Path]
) -> tuple[dict[str, Any], dict[str, Any]]:
    pinned = {
        "mission_id": mission_id,
        "workspaces": {
            workspace: {"commit_sha": next(
                str(node.get("commit_sha") or "") for node in mission["nodes"]
                if node.get("workspace_id") == workspace
            )}
            for workspace in roots
        },
    }
    runtime = {
        **pinned,
        "workspaces": {
            workspace: {**pinned["workspaces"][workspace], "root": str(root)}
            for workspace, root in roots.items()
        },
    }
    return pinned, runtime


def verify_mission(mission_id: str) -> dict[str, Any]:
    from app.workspace_missions.service import refresh_mission

    mission = refresh_mission(mission_id)
    if mission is None:
        raise ValueError(f"mission not found: {mission_id}")
    if mission.get("status") != "verifying":
        raise ValueError(f"mission is not ready for verification ({mission.get('status')})")
    gated = _green_delivery_gate(mission_id, mission)
    if gated is not None:
        return gated
    commands = _verification_commands(mission)
    if len(mission.get("nodes") or []) > 1 and not commands:
        return workspace_mission_store.update_mission(
            mission_id, status="blocked",
            blocker="cross-workspace verification commands are not configured",
            blocker_code="configuration",
        ) or mission
    roots: dict[str, Path] = {}
    isolation_roots: list[Path] = []
    try:
        roots, isolation_roots = _materialize_pinned_roots(mission_id, mission)
        pinned, runtime_manifest = _manifests(mission_id, mission, roots)
        workspace_mission_store.update_mission(mission_id, integration_manifest=pinned)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as handle:
            json.dump(runtime_manifest, handle, sort_keys=True)
            manifest_path = handle.name
        env = dict(os.environ)
        env["AXON_MISSION_MANIFEST"] = manifest_path
        for workspace, root in roots.items():
            key = re.sub(r"[^A-Z0-9]+", "_", workspace.upper()).strip("_")
            env[f"AXON_MISSION_{key}_ROOT"] = str(root)
        receipts: list[dict[str, Any]] = []
        for workspace, command in commands:
            root = roots.get(workspace)
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
                    blocker_code="verification_failed",
                ) or mission
        for node in mission.get("nodes") or []:
            workspace_mission_store.update_node(
                str(node["node_id"]), verification={"status": "passed", "receipts": receipts}
            )
        return workspace_mission_store.update_mission(
            mission_id, status="ready_for_promotion", blocker="", blocker_code=""
        ) or mission
    except ValueError as exc:
        return workspace_mission_store.update_mission(
            mission_id, status="blocked", blocker=str(exc), blocker_code="verification_error"
        ) or mission
    finally:
        from app.safe_improvement.isolated_executor import cleanup_isolation_root

        for root in isolation_roots:
            cleanup_isolation_root(root)
        if "manifest_path" in locals():
            Path(manifest_path).unlink(missing_ok=True)


def _record_promotion(
    mission_id: str, node: dict[str, Any], status: str, detail: str
) -> None:
    mission = workspace_mission_store.get_mission(mission_id) or {}
    records = list(mission.get("promotions") or [])
    record = {
        "node_id": node.get("node_id"), "workspace_id": node.get("workspace_id"),
        "commit_sha": node.get("commit_sha"), "draft_pr_url": node.get("draft_pr_url"),
        "status": status, "detail": detail,
    }
    records = [item for item in records if item.get("node_id") != node.get("node_id")]
    workspace_mission_store.update_mission(mission_id, promotions=[*records, record])


def promote_mission(mission_id: str) -> dict[str, Any]:
    mission = workspace_mission_store.get_mission(mission_id)
    if mission is None:
        raise ValueError(f"mission not found: {mission_id}")
    if mission.get("status") != "ready_for_promotion":
        raise ValueError(f"mission is not ready for promotion ({mission.get('status')})")
    if str(mission.get("risk") or "normal") not in {"low", "normal"}:
        return workspace_mission_store.update_mission(
            mission_id, blocker="operator approval required for elevated mission risk",
            blocker_code="approval_required",
        ) or mission
    for node in mission.get("nodes") or []:
        if node.get("relation") == "impact_review":
            continue
        workspace = str(node.get("workspace_id") or "")
        policy = get_workspace_delivery_policy(workspace)
        if policy is None or is_protected_branch(policy, policy.base_branch):
            _record_promotion(mission_id, node, "approval_required", "protected integration branch")
            return workspace_mission_store.update_mission(
                mission_id, blocker=f"operator approval required for protected promotion in {workspace}",
                blocker_code="approval_required",
            ) or mission
        if str(node.get("delivery_stage") or "") == "no_change":
            _record_promotion(mission_id, node, "no_change", "nothing to promote")
            continue
        pr_url = str(node.get("draft_pr_url") or "").strip()
        if not pr_url:
            raise ValueError(f"mission node has no draft PR: {workspace}")
        ready = subprocess.run(
            ["gh", "pr", "ready", pr_url], capture_output=True, text=True,
            timeout=120, check=False,
        )
        if ready.returncode != 0 and "already marked ready" not in (ready.stderr or ready.stdout).lower():
            detail = (ready.stderr or ready.stdout).strip()
            _record_promotion(mission_id, node, "failed", detail)
            return workspace_mission_store.update_mission(
                mission_id, status="blocked",
                blocker=f"could not mark draft PR ready in {workspace}: {detail}",
                blocker_code="promotion_failed",
            ) or mission
        result = subprocess.run(
            ["gh", "pr", "merge", pr_url, "--merge", "--delete-branch"],
            capture_output=True, text=True, timeout=120, check=False,
        )
        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip()
            _record_promotion(mission_id, node, "failed", detail)
            return workspace_mission_store.update_mission(
                mission_id, status="blocked", blocker=f"promotion failed in {workspace}: {detail}",
                blocker_code="promotion_failed",
            ) or mission
        _record_promotion(mission_id, node, "promoted", pr_url)
    return workspace_mission_store.update_mission(
        mission_id, status="completed", blocker="", blocker_code=""
    ) or mission


__all__ = ["promote_mission", "verify_mission"]
