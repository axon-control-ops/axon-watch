"""Load per-workspace worker delivery policy from config/workspace-delivery.json."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class WorkspaceDeliveryPolicy:
    enabled: bool
    workspace_id: str
    base_branch: str
    github_owner: str
    github_repo: str
    workflow_names: tuple[str, ...]
    attempt_budget: int
    push_policy: str
    owner_role: str
    escalate_role: str
    lead_role: str
    ci_poll_timeout_seconds: int
    protected_branches: tuple[str, ...] = field(default_factory=tuple)


_CACHE: dict[str, WorkspaceDeliveryPolicy] | None = None


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def default_config_path() -> Path:
    configured = os.environ.get("AXON_WATCH_WORKSPACE_DELIVERY_FILE", "").strip()
    if configured:
        path = Path(configured).expanduser()
        if not path.is_absolute():
            path = (_repo_root() / path).resolve()
        return path
    return (_repo_root() / "config" / "workspace-delivery.json").resolve()


def clear_config_cache_for_tests() -> None:
    global _CACHE
    _CACHE = None


def _as_int(value: Any, default: int, *, lo: int = 1, hi: int = 32) -> int:
    try:
        return max(lo, min(int(value), hi))
    except (TypeError, ValueError):
        return default


def _policy_from_row(
    row: dict[str, Any],
    defaults: dict[str, Any],
) -> WorkspaceDeliveryPolicy | None:
    workspace_id = str(row.get("workspace_id") or "").strip()
    if not workspace_id:
        return None
    owner = str(row.get("github_owner") or "").strip()
    repo = str(row.get("github_repo") or "").strip()
    base = str(row.get("base_branch") or defaults.get("base_branch") or "dev").strip() or "dev"
    workflows_raw = row.get("workflow_names") or defaults.get("workflow_names") or []
    workflows: list[str] = []
    if isinstance(workflows_raw, list):
        workflows = [str(item).strip() for item in workflows_raw if str(item).strip()]
    protected_raw = row.get("protected_branches") or defaults.get("protected_branches") or []
    protected: list[str] = []
    if isinstance(protected_raw, list):
        protected = [str(item).strip() for item in protected_raw if str(item).strip()]
    if not protected:
        protected = ["main", "master", "dev", "production", "release"]
    return WorkspaceDeliveryPolicy(
        enabled=bool(row.get("enabled", defaults.get("enabled", True))),
        workspace_id=workspace_id,
        base_branch=base,
        github_owner=owner,
        github_repo=repo,
        workflow_names=tuple(workflows),
        attempt_budget=_as_int(
            row.get("attempt_budget", defaults.get("attempt_budget", 3)),
            3,
        ),
        push_policy=str(
            row.get("push_policy") or defaults.get("push_policy") or "draft_pr"
        ).strip()
        or "draft_pr",
        owner_role=str(row.get("owner_role") or defaults.get("owner_role") or "watcher")
        .strip()
        .lower()
        or "watcher",
        escalate_role=str(
            row.get("escalate_role") or defaults.get("escalate_role") or "integrations"
        )
        .strip()
        .lower()
        or "integrations",
        lead_role=str(row.get("lead_role") or defaults.get("lead_role") or "lead")
        .strip()
        .lower()
        or "lead",
        ci_poll_timeout_seconds=_as_int(
            row.get(
                "ci_poll_timeout_seconds",
                defaults.get("ci_poll_timeout_seconds", 1800),
            ),
            1800,
            lo=60,
            hi=86_400,
        ),
        protected_branches=tuple(protected),
    )


def load_workspace_delivery_policies(
    *,
    path: Path | None = None,
    force_reload: bool = False,
) -> dict[str, WorkspaceDeliveryPolicy]:
    global _CACHE
    if _CACHE is not None and not force_reload and path is None:
        return dict(_CACHE)
    config_path = path or default_config_path()
    if not config_path.is_file():
        _CACHE = {}
        return {}
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        _CACHE = {}
        return {}
    defaults = payload.get("defaults") if isinstance(payload.get("defaults"), dict) else {}
    rows = payload.get("workspaces") if isinstance(payload.get("workspaces"), list) else []
    policies: dict[str, WorkspaceDeliveryPolicy] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        policy = _policy_from_row(row, defaults)
        if policy is not None:
            policies[policy.workspace_id] = policy
    _CACHE = policies
    return dict(policies)


def get_workspace_delivery_policy(workspace_id: str) -> WorkspaceDeliveryPolicy | None:
    cleaned = workspace_id.strip()
    if not cleaned:
        return None
    return load_workspace_delivery_policies().get(cleaned)


def is_protected_branch(policy: WorkspaceDeliveryPolicy, branch: str) -> bool:
    name = branch.strip().lower()
    return name in {item.lower() for item in policy.protected_branches}
