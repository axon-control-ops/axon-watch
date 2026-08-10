"""Sanitized Sentry credential validation for the operator Vault surface."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen as sentry_urlopen

from app.adapters.watch_client import post_watch_sentry_probe_write

from .routes import get_vault_secret, list_vault_secrets

TOKEN_KEYS = ("SENTRY_AUTH_TOKEN", "SENTRY_API_TOKEN")
ORG_KEYS = ("SENTRY_ORG_SLUG", "DASHPRO_SENTRY_ORG_SLUG")
PROJECT_KEYS = ("SENTRY_PROJECT_SLUG", "DASHPRO_SENTRY_PROJECT_SLUG")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _token_fingerprint(token: str) -> dict[str, object]:
    stripped = token.strip()
    if not stripped:
        return {"token_prefix": "", "token_length": 0}
    return {
        "token_prefix": f"{stripped[:6]}…",
        "token_length": len(stripped),
    }


def _safe_detail(detail: str, token: str) -> str:
    cleaned = detail.strip()
    if token:
        cleaned = cleaned.replace(token, "[redacted]")
    return cleaned[:500]


def _secret_value(detail: dict[str, Any]) -> str:
    for key in ("password", "value", "notes", "url"):
        value = str(detail.get(key) or "").strip()
        if value:
            return value
    return ""


def _load_vault_values() -> dict[str, str]:
    values: dict[str, str] = {}
    for secret in list_vault_secrets():
        name = str(secret.get("name") or "").strip()
        if name not in (*TOKEN_KEYS, *ORG_KEYS, *PROJECT_KEYS):
            continue
        secret_id = secret.get("id")
        if not isinstance(secret_id, int):
            try:
                secret_id = int(str(secret_id))
            except (TypeError, ValueError):
                continue
        detail = get_vault_secret(secret_id)
        value = _secret_value(detail)
        if value:
            values[name] = value
    return values


def _first_value(values: dict[str, str], keys: tuple[str, ...]) -> tuple[str, str]:
    for key in keys:
        value = values.get(key, "").strip()
        if value:
            return key, value
    return "", ""


def _read_sentry_projects(
    *,
    token: str,
    org_slug: str,
    timeout_seconds: float = 15.0,
) -> tuple[bool, int | None, list[str], str]:
    url = f"https://sentry.io/api/0/organizations/{quote(org_slug)}/projects/"
    request = Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "User-Agent": "Axon-X-Control-Plane/1.0",
        },
    )
    try:
        with sentry_urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read().decode("utf-8", errors="replace")
            status = int(getattr(response, "status", 200) or 200)
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return False, int(exc.code), [], _safe_detail(body or str(exc), token)
    except (TimeoutError, URLError, OSError) as exc:
        return False, None, [], _safe_detail(str(exc), token)

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return False, status, [], "Sentry returned non-JSON project payload"

    if not isinstance(payload, list):
        return False, status, [], "Sentry project payload was not a list"

    projects: list[str] = []
    for item in payload:
        if isinstance(item, dict):
            slug = str(item.get("slug") or "").strip()
            if slug:
                projects.append(slug)
    return 200 <= status < 300, status, projects, ""


def validate_sentry_vault_credentials() -> dict[str, object]:
    """Validate Sentry Vault keys without returning secret material."""

    checked_at = _now_iso()
    try:
        values = _load_vault_values()
    except RuntimeError as exc:
        return {
            "ok": False,
            "present": False,
            "read_ok": False,
            "write_ok": False,
            "project_found": False,
            "checked_at": checked_at,
            "detail": str(exc),
        }

    token_key, token = _first_value(values, TOKEN_KEYS)
    org_key, org_slug = _first_value(values, ORG_KEYS)
    project_key, project_slug = _first_value(values, PROJECT_KEYS)

    result: dict[str, object] = {
        "ok": False,
        "present": bool(token and org_slug and project_slug),
        "read_ok": False,
        "write_ok": False,
        "project_found": False,
        "checked_at": checked_at,
        "token_key": token_key,
        "org_key": org_key,
        "project_key": project_key,
        "org_slug": org_slug,
        "project_slug": project_slug,
        **_token_fingerprint(token),
    }

    missing = []
    if not token:
        missing.append("SENTRY_AUTH_TOKEN or SENTRY_API_TOKEN")
    if not org_slug:
        missing.append("SENTRY_ORG_SLUG or DASHPRO_SENTRY_ORG_SLUG")
    if not project_slug:
        missing.append("SENTRY_PROJECT_SLUG or DASHPRO_SENTRY_PROJECT_SLUG")
    if missing:
        result["detail"] = f"Missing Vault key(s): {', '.join(missing)}"
        return result

    read_ok, status_code, projects, read_detail = _read_sentry_projects(
        token=token,
        org_slug=org_slug,
    )
    project_found = project_slug in projects
    result.update(
        {
            "read_ok": read_ok,
            "status_code": status_code,
            "project_found": project_found,
            "visible_project_count": len(projects),
        }
    )
    if read_detail:
        result["detail"] = read_detail

    write_probe = post_watch_sentry_probe_write()
    if isinstance(write_probe, dict):
        result["write_ok"] = bool(write_probe.get("ok") and write_probe.get("write_scope"))
        result["write_detail"] = str(write_probe.get("detail") or write_probe.get("reason") or "").strip()
    else:
        result["write_ok"] = False
        result["write_detail"] = "Watch Sentry write probe unavailable"

    result["ok"] = bool(result["present"] and result["read_ok"] and result["project_found"] and result["write_ok"])
    if not result.get("detail"):
        if not result["read_ok"]:
            result["detail"] = "Sentry read probe failed"
        elif not result["project_found"]:
            result["detail"] = f"Sentry project '{project_slug}' was not visible to this token"
        elif not result["write_ok"]:
            result["detail"] = "Sentry write-scope probe failed"
        else:
            result["detail"] = "Sentry token validated for Vault monitor use"
    return result
