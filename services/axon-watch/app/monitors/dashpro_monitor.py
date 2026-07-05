"""Run bounded DashPro external monitor checks and return signal-ready records."""

from __future__ import annotations

import json
from pathlib import Path

from app.monitors.dashpro_posthog import check_posthog_recent_events
from app.monitors.dashpro_sentry import check_sentry_recent_issues
from app.vault.credential_resolver import merge_monitor_env


def _service_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _repo_root() -> Path:
    return _service_root().parent.parent


def _default_config_path() -> Path:
    return (_repo_root() / "config" / "dashpro-monitor-slice.json").resolve()

def load_monitor_config(path: Path | None = None) -> dict[str, object]:
    config_path = path or _default_config_path()
    if not config_path.is_file():
        return {}
    return json.loads(config_path.read_text(encoding="utf-8"))


def probe_dashpro_monitor_records() -> list[dict[str, object]]:
    config = load_monitor_config()
    if not config.get("enabled", True):
        return []

    workspace_id = str(config.get("workspace_id") or "workspace_dashpro").strip()
    project_root_raw = str(config.get("project_root") or "").strip()
    if not project_root_raw:
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
        else:
            continue

        records.append(
            {
                "check_id": check_id,
                "check_type": check_type,
                "workspace_id": workspace_id,
                "service": str(entry.get("service") or check_type),
                "status": status,
                "detail": detail,
            }
        )

    return records
