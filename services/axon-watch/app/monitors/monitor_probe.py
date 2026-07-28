"""Run bounded external monitor checks for a workspace monitor slice."""

from __future__ import annotations

import os
from pathlib import Path

from app.monitors.dashpro_posthog import check_posthog_recent_events
from app.monitors.dashpro_sentry import check_sentry_recent_issues
from app.monitors.dashpro_supabase_storage import check_supabase_storage_quota
from app.monitors.http_health import check_http_health
from app.monitors.slice_registry import load_monitor_slices
from app.vault.credential_resolver import merge_monitor_env


def _resolve_url(raw: str, env: dict[str, str]) -> str:
    text = str(raw or "").strip()
    if not text:
        return ""
    for key, value in env.items():
        text = text.replace(f"${{{key}}}", str(value))
        text = text.replace(f"${key}", str(value))
    return text.strip()


def _checks_are_http_health_only(checks: object) -> bool:
    if not isinstance(checks, list) or not checks:
        return False
    for entry in checks:
        if not isinstance(entry, dict):
            return False
        if str(entry.get("type") or "").strip() != "http_health":
            return False
    return True


def probe_monitor_slice(config: dict[str, object]) -> list[dict[str, object]]:
    if not config.get("enabled", True):
        return []

    workspace_id = str(config.get("workspace_id") or "").strip()
    workspace_label = str(config.get("workspace_label") or workspace_id or "workspace").strip()
    project_root_raw = str(config.get("project_root") or "").strip()
    checks = config.get("checks")
    if not workspace_id:
        return []

    env: dict[str, str] = {key: str(value) for key, value in os.environ.items()}
    if project_root_raw:
        project_root = Path(project_root_raw).expanduser().resolve()
        if project_root.is_dir():
            env = merge_monitor_env(project_root=project_root)
        elif not _checks_are_http_health_only(checks):
            return []
    elif not _checks_are_http_health_only(checks):
        return []

    records: list[dict[str, object]] = []
    if not isinstance(checks, list):
        return records

    for entry in checks:
        if not isinstance(entry, dict):
            continue
        check_id = str(entry.get("id") or "").strip()
        check_type = str(entry.get("type") or "").strip()
        if not check_id or not check_type:
            continue

        issues: list[dict[str, object]] = []
        if check_type == "sentry_recent_issues":
            environment = str(entry.get("environment") or "").strip() or None
            status, detail, issues = check_sentry_recent_issues(
                env=env,
                environment=environment,
                workspace_id=workspace_id,
            )
        elif check_type == "posthog_recent_events":
            status, detail = check_posthog_recent_events(env=env)
        elif check_type == "supabase_storage_quota":
            status, detail = check_supabase_storage_quota(env=env)
        elif check_type == "http_health":
            url = _resolve_url(str(entry.get("url") or ""), env)
            expect_status = int(entry.get("expect_status") or 200)
            expect_json_status = str(entry.get("expect_json_status") or "").strip() or None
            timeout_seconds = float(entry.get("timeout_seconds") or 5.0)
            status, detail = check_http_health(
                url=url,
                timeout_seconds=timeout_seconds,
                expect_status=expect_status,
                expect_json_status=expect_json_status,
            )
        else:
            continue

        record: dict[str, object] = {
            "check_id": check_id,
            "check_type": check_type,
            "workspace_id": workspace_id,
            "workspace_label": workspace_label,
            "service": str(entry.get("service") or check_type),
            "status": status,
            "detail": detail,
        }
        if check_type == "sentry_recent_issues" and issues:
            record["issues"] = issues
        if status == "skipped":
            record["vault_action"] = {
                "surface": "/vault",
                "hint": f"Add missing monitor credentials in Vault for {workspace_label}",
            }
        records.append(record)

    return records


def probe_all_monitor_slices(config_dir: Path | None = None) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for config in load_monitor_slices(config_dir):
        records.extend(probe_monitor_slice(config))
    return records
