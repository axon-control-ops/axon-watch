"""Run bounded external monitor checks for a workspace monitor slice."""

from __future__ import annotations

from pathlib import Path

from app.monitors.dashpro_posthog import check_posthog_recent_events
from app.monitors.dashpro_sentry import check_sentry_recent_issues
from app.monitors.dashpro_supabase_storage import check_supabase_storage_quota
from app.vault.credential_resolver import merge_monitor_env


def probe_monitor_slice(config: dict[str, object]) -> list[dict[str, object]]:
    if not config.get("enabled", True):
        return []

    workspace_id = str(config.get("workspace_id") or "").strip()
    workspace_label = str(config.get("workspace_label") or workspace_id or "workspace").strip()
    project_root_raw = str(config.get("project_root") or "").strip()
    if not workspace_id or not project_root_raw:
        return []

    project_root = Path(project_root_raw).expanduser().resolve()
    if not project_root.is_dir():
        return []

    env = merge_monitor_env(project_root=project_root)
    records: list[dict[str, object]] = []

    checks = config.get("checks")
    if not isinstance(checks, list):
        return records

    for entry in checks:
        if not isinstance(entry, dict):
            continue
        check_id = str(entry.get("id") or "").strip()
        check_type = str(entry.get("type") or "").strip()
        if not check_id or not check_type:
            continue

        if check_type == "sentry_recent_issues":
            status, detail = check_sentry_recent_issues(env=env)
        elif check_type == "posthog_recent_events":
            status, detail = check_posthog_recent_events(env=env)
        elif check_type == "supabase_storage_quota":
            status, detail = check_supabase_storage_quota(env=env)
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
        if status == "skipped":
            record["vault_action"] = {
                "surface": "/vault",
                "hint": f"Add missing monitor credentials in Vault for {workspace_label}",
            }
        records.append(record)

    return records


def probe_all_monitor_slices(config_dir: Path | None = None) -> list[dict[str, object]]:
    from app.monitors.slice_registry import load_monitor_slices

    records: list[dict[str, object]] = []
    for config in load_monitor_slices(config_dir):
        records.extend(probe_monitor_slice(config))
    return records
