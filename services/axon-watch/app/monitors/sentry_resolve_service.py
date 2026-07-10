"""Operator Sentry resolve helpers for the watch service."""

from __future__ import annotations

from pathlib import Path

from app.monitors.sentry_api import probe_sentry_write_scope, resolve_sentry_issue
from app.monitors.slice_registry import load_monitor_slices
from app.vault.credential_resolver import merge_monitor_env


def _dashpro_project_root() -> Path | None:
    for config in load_monitor_slices():
        if not config.get("enabled", True):
            continue
        checks = config.get("checks")
        if not isinstance(checks, list):
            continue
        has_sentry = any(
            isinstance(entry, dict) and str(entry.get("type") or "").strip() == "sentry_recent_issues"
            for entry in checks
        )
        if not has_sentry:
            continue
        project_root_raw = str(config.get("project_root") or "").strip()
        if not project_root_raw:
            continue
        project_root = Path(project_root_raw).expanduser().resolve()
        if project_root.is_dir():
            return project_root
    return None


def resolve_watch_sentry_issue(
    issue_id: str,
    *,
    status: str = "resolved",
    requested_by: str = "operator",
) -> dict[str, object]:
    project_root = _dashpro_project_root()
    if project_root is None:
        return {
            "ok": False,
            "reason": "missing_monitor_slice",
            "issue_id": str(issue_id or "").strip(),
            "detail": "No enabled DashPro Sentry monitor slice with a valid project_root.",
        }
    env = merge_monitor_env(project_root=project_root)
    result = resolve_sentry_issue(issue_id, env=env, status=status)
    if isinstance(result, dict):
        result = {**result, "requested_by": str(requested_by or "operator").strip() or "operator"}
    return result


def probe_watch_sentry_write_scope() -> dict[str, object]:
    project_root = _dashpro_project_root()
    if project_root is None:
        return {
            "ok": False,
            "write_scope": False,
            "reason": "missing_monitor_slice",
            "detail": "No enabled DashPro Sentry monitor slice with a valid project_root.",
        }
    env = merge_monitor_env(project_root=project_root)
    return probe_sentry_write_scope(env=env)
