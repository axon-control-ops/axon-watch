"""Load Gate 9 CI remediation bindings from config/ci-remediation.json."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CiRemediationBinding:
    enabled: bool
    workspace_id: str
    github_owner: str
    github_repo: str
    workflow_name: str
    attempt_budget: int
    push_policy: str
    owner_role: str
    escalate_role: str
    lead_role: str
    dispatch_on_ingest: bool


_CACHE: list[CiRemediationBinding] | None = None


def _repo_root() -> Path:
    # …/services/control-plane/app/ci_remediation/config.py → parents[4] = repo root
    return Path(__file__).resolve().parents[4]


def default_config_path() -> Path:
    configured = os.environ.get("AXON_WATCH_CI_REMEDIATION_FILE", "").strip()
    if configured:
        path = Path(configured).expanduser()
        if not path.is_absolute():
            path = (_repo_root() / path).resolve()
        return path
    return (_repo_root() / "config" / "ci-remediation.json").resolve()


def clear_config_cache_for_tests() -> None:
    global _CACHE
    _CACHE = None


def _as_int(value: Any, default: int) -> int:
    try:
        return max(1, min(int(value), 32))
    except (TypeError, ValueError):
        return default


def _binding_from_row(row: dict[str, Any], defaults: dict[str, Any]) -> CiRemediationBinding | None:
    workspace_id = str(row.get("workspace_id") or "").strip()
    owner = str(row.get("github_owner") or "").strip()
    repo = str(row.get("github_repo") or "").strip()
    workflow = str(row.get("workflow_name") or "").strip()
    if not workspace_id or not owner or not repo or not workflow:
        return None
    return CiRemediationBinding(
        enabled=bool(row.get("enabled", False)),
        workspace_id=workspace_id,
        github_owner=owner,
        github_repo=repo,
        workflow_name=workflow,
        attempt_budget=_as_int(
            row.get("attempt_budget", defaults.get("attempt_budget", 3)),
            3,
        ),
        push_policy=str(
            row.get("push_policy") or defaults.get("push_policy") or "draft_pr"
        ).strip()
        or "draft_pr",
        owner_role=str(
            row.get("owner_role") or defaults.get("owner_role") or "watcher"
        )
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
        dispatch_on_ingest=bool(
            row.get(
                "dispatch_on_ingest",
                defaults.get("dispatch_on_ingest", True),
            )
        ),
    )


def load_ci_remediation_config(
    *,
    path: Path | None = None,
    force_reload: bool = False,
) -> list[CiRemediationBinding]:
    global _CACHE
    if _CACHE is not None and not force_reload and path is None:
        return list(_CACHE)
    config_path = path or default_config_path()
    if not config_path.is_file():
        _CACHE = []
        return []
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        _CACHE = []
        return []
    defaults = payload.get("defaults") if isinstance(payload.get("defaults"), dict) else {}
    rows = payload.get("bindings") if isinstance(payload.get("bindings"), list) else []
    bindings: list[CiRemediationBinding] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        binding = _binding_from_row(row, defaults)
        if binding is not None:
            bindings.append(binding)
    _CACHE = bindings
    return list(bindings)


def match_binding(
    *,
    github_owner: str,
    github_repo: str,
    workflow_name: str,
    enabled_only: bool = True,
) -> CiRemediationBinding | None:
    owner = github_owner.strip().lower()
    repo = github_repo.strip().lower()
    workflow = workflow_name.strip().lower()
    for binding in load_ci_remediation_config():
        if enabled_only and not binding.enabled:
            continue
        if (
            binding.github_owner.lower() == owner
            and binding.github_repo.lower() == repo
            and binding.workflow_name.lower() == workflow
        ):
            return binding
    return None
