"""Sentry write client for Axon-Watch (resolve + write-scope probe)."""

from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.monitors.dashpro_sentry import _sentry_org_slug


def _sentry_token(env: dict[str, str]) -> str:
    return str(env.get("SENTRY_AUTH_TOKEN") or env.get("SENTRY_API_TOKEN") or "").strip()


def _sentry_settings_from_env(env: dict[str, str]) -> dict[str, str]:
    return {
        "token": _sentry_token(env),
        "org": _sentry_org_slug(env),
    }


def resolve_sentry_issue(
    issue_id: str,
    *,
    env: dict[str, str],
    status: str = "resolved",
    timeout_seconds: float = 15,
) -> dict[str, Any]:
    """PUT organization issue status on Sentry (requires event:write or project:write)."""
    normalized_issue_id = str(issue_id or "").strip()
    if not normalized_issue_id:
        return {"ok": False, "reason": "missing_issue_id"}

    cfg = _sentry_settings_from_env(env)
    if not cfg["token"] or not cfg["org"]:
        return {"ok": False, "reason": "missing_config", "issue_id": normalized_issue_id}

    url = f"https://sentry.io/api/0/organizations/{cfg['org']}/issues/{normalized_issue_id}/"
    payload = {"status": str(status or "resolved").strip() or "resolved"}
    body = json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        data=body,
        method="PUT",
        headers={
            "Authorization": f"Bearer {cfg['token']}",
            "Content-Type": "application/json",
            "User-Agent": "Axon-Watch-Sentry-Write/1.0",
        },
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            status_code = int(response.status)
            raw = response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        status_code = int(exc.code)
        raw = exc.read().decode("utf-8", errors="replace")
    except (TimeoutError, URLError, OSError) as exc:
        return {"ok": False, "issue_id": normalized_issue_id, "reason": str(exc)}

    try:
        response_payload: Any = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        response_payload = {"raw": raw[:400]}

    if status_code not in {200, 201}:
        reason = "missing_write_scope" if status_code == 403 else "resolve_failed"
        return {
            "ok": False,
            "reason": reason,
            "issue_id": normalized_issue_id,
            "status_code": status_code,
            "detail": (
                "Grant event:write (or project:write) on the Sentry auth token "
                "to resolve issues from Axon."
                if status_code == 403
                else ""
            ),
            "payload": response_payload,
        }

    resolved_status = payload["status"]
    if isinstance(response_payload, dict):
        resolved_status = str(response_payload.get("status") or resolved_status).strip()
    return {
        "ok": True,
        "issue_id": normalized_issue_id,
        "status": resolved_status,
        "payload": response_payload,
    }


def probe_sentry_write_scope(
    *,
    env: dict[str, str],
    timeout_seconds: float = 10,
) -> dict[str, Any]:
    """Probe whether the token can update issues (PUT probe id 0 → 404 means write-capable)."""
    cfg = _sentry_settings_from_env(env)
    if not cfg["token"] or not cfg["org"]:
        return {
            "ok": False,
            "write_scope": False,
            "reason": "missing_config",
            "detail": "SENTRY_AUTH_TOKEN and SENTRY_ORG_SLUG are required.",
        }

    url = f"https://sentry.io/api/0/organizations/{cfg['org']}/issues/0/"
    body = json.dumps({"status": "resolved"}).encode("utf-8")
    request = Request(
        url,
        data=body,
        method="PUT",
        headers={
            "Authorization": f"Bearer {cfg['token']}",
            "Content-Type": "application/json",
            "User-Agent": "Axon-Watch-Sentry-Write/1.0",
        },
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            status_code = int(response.status)
            raw = response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        status_code = int(exc.code)
        raw = exc.read().decode("utf-8", errors="replace")
    except (TimeoutError, URLError, OSError) as exc:
        return {"ok": False, "write_scope": False, "reason": str(exc)}

    try:
        payload: Any = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        payload = {"raw": raw[:400]}

    if status_code == 404:
        return {
            "ok": True,
            "write_scope": True,
            "status_code": status_code,
            "detail": "Token can update issues (probe issue id was not found, as expected).",
        }
    if status_code == 403:
        return {
            "ok": False,
            "write_scope": False,
            "reason": "missing_write_scope",
            "status_code": status_code,
            "detail": "Token is read-only. Use a personal token with event:write or project:write.",
            "payload": payload,
        }
    return {
        "ok": False,
        "write_scope": False,
        "reason": "probe_failed",
        "status_code": status_code,
        "payload": payload,
    }
