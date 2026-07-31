"""Run bounded external monitor checks for a workspace monitor slice."""

from __future__ import annotations

import os
from pathlib import Path

from app.monitors.dashpro_posthog import check_posthog_recent_events
from app.monitors.dashpro_sentry import check_sentry_recent_issues
from app.monitors.dashpro_supabase_storage import check_supabase_storage_quota
from app.monitors.github_probe_headers import (
    github_api_headers,
    is_github_api_url,
    looks_like_github_token,
    resolve_github_token,
)
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


def _first_env_token(env: dict[str, str], names: tuple[str, ...]) -> str:
    for name in names:
        token = str(env.get(name) or "").strip()
        if token:
            return token
    return ""


def _http_health_headers(entry: dict[str, object], env: dict[str, str], *, url: str) -> dict[str, str]:
    """Build optional auth headers for HTTP health checks (GitHub token when present)."""
    headers: dict[str, str] = {}
    if is_github_api_url(url):
        headers.update(github_api_headers(env))

    raw_headers = entry.get("headers")
    if isinstance(raw_headers, dict):
        for key, value in raw_headers.items():
            name = str(key or "").strip()
            if not name:
                continue
            headers[name] = _resolve_url(str(value or ""), env)

    bearer_env = str(entry.get("bearer_token_env") or "").strip()
    # Explicit bearer_token_env wins over auto-detected GitHub token so a
    # workspace dotenv placeholder cannot shadow a Vault GH_TOKEN — unless the
    # explicit value itself is a placeholder.
    if bearer_env:
        token = _first_env_token(env, (bearer_env,))
        if token and (looks_like_github_token(token) or not is_github_api_url(url)):
            headers["Authorization"] = f"Bearer {token}"
    elif is_github_api_url(url):
        token = resolve_github_token(env)
        if token and "authorization" not in {key.lower() for key in headers}:
            headers["Authorization"] = f"Bearer {token}"
    return {key: value for key, value in headers.items() if str(value).strip()}


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
        url = ""
        request_headers: dict[str, str] = {}
        if check_type == "sentry_recent_issues":
            environment = str(entry.get("environment") or "").strip() or None
            status, detail, issues = check_sentry_recent_issues(
                env=env,
                environment=environment,
                workspace_id=workspace_id,
            )
        elif check_type == "posthog_recent_events":
            limit = max(1, int(entry.get("limit") or 5))
            if entry.get("timeout_ms") is not None:
                timeout_seconds = max(1.0, float(entry.get("timeout_ms") or 20000) / 1000.0)
            else:
                timeout_seconds = max(1.0, float(entry.get("timeout_seconds") or 20))
            retries = max(0, int(entry.get("retries") or 1))
            status, detail = check_posthog_recent_events(
                env=env,
                limit=limit,
                timeout_seconds=timeout_seconds,
                retries=retries,
            )
        elif check_type == "supabase_storage_quota":
            status, detail = check_supabase_storage_quota(env=env)
        elif check_type == "http_health":
            url = _resolve_url(str(entry.get("url") or ""), env)
            expect_status = int(entry.get("expect_status") or 200)
            expect_json_status = str(entry.get("expect_json_status") or "").strip() or None
            timeout_seconds = float(entry.get("timeout_seconds") or 5.0)
            request_headers = _http_health_headers(entry, env, url=url)
            status, detail = check_http_health(
                url=url,
                timeout_seconds=timeout_seconds,
                expect_status=expect_status,
                expect_json_status=expect_json_status,
                headers=request_headers or None,
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
        elif (
            check_type == "http_health"
            and status == "warning"
            and is_github_api_url(url)
            and (
                "rate limit" in str(detail).lower()
                or "missing probe token" in str(detail).lower()
                or "placeholder probe token" in str(detail).lower()
            )
            and "authorization" not in {key.lower() for key in request_headers}
        ):
            record["vault_action"] = {
                "surface": "/vault",
                "hint": (
                    f"Add GH_TOKEN or GITHUB_TOKEN in Vault for {workspace_label} "
                    "so GitHub API health checks use the authenticated quota"
                ),
            }
        records.append(record)

    return records


def probe_all_monitor_slices(config_dir: Path | None = None) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for config in load_monitor_slices(config_dir):
        records.extend(probe_monitor_slice(config))
    return records
