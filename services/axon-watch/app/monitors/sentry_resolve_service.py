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
        if result.get("ok"):
            # Drop stale monitor samples so the next inbox/briefing poll omits this issue.
            from app.monitors.dashpro_monitor import reset_monitor_probe_cache

            reset_monitor_probe_cache()
    return result


def attend_watch_sentry_issue(
    issue_id: str,
    *,
    confirm_release: str = "",
    requested_by: str = "operator",
    mark_resolved_in_next_release: bool = True,
    workspace_id: str = "workspace_dashpro",
) -> dict[str, object]:
    """Mark a production Sentry issue attended after OTA/new build and mute until newer release."""
    from app.signals.sentry_issue_attendance_store import attend_issue

    cleaned_issue = str(issue_id or "").strip()
    if not cleaned_issue:
        return {"ok": False, "reason": "missing_issue_id"}

    release = str(confirm_release or "").strip() or "attended"
    attendance = attend_issue(
        issue_id=cleaned_issue,
        workspace_id=workspace_id,
        confirm_release=release,
        attended_by=requested_by,
    )

    sentry_result: dict[str, object] | None = None
    if mark_resolved_in_next_release:
        sentry_result = resolve_watch_sentry_issue(
            cleaned_issue,
            status="resolvedInNextRelease",
            requested_by=requested_by,
        )
    else:
        from app.monitors.dashpro_monitor import reset_monitor_probe_cache

        reset_monitor_probe_cache()

    ok = True
    if sentry_result is not None and not sentry_result.get("ok"):
        # Local attend still stands even if Sentry write fails (token scope).
        ok = True
    return {
        "ok": ok,
        "issue_id": cleaned_issue,
        "attendance": attendance,
        "sentry": sentry_result,
        "detail": (
            "Attended after OTA/build — suppressed in Axon until a newer production release "
            "reports this issue again."
        ),
    }


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
