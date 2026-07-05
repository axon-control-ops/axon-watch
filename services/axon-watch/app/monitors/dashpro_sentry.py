"""DashPro Sentry monitor check (bounded port of axon-local slice)."""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def _sentry_org_slug(env: dict[str, str]) -> str:
    return str(env.get("SENTRY_ORG_SLUG") or "edudashpro").strip()


def _sentry_project_slug(env: dict[str, str]) -> str:
    explicit = str(env.get("SENTRY_PROJECT_SLUG") or "").strip()
    if explicit:
        return explicit
    dsn = str(env.get("EXPO_PUBLIC_SENTRY_DSN") or env.get("NEXT_PUBLIC_SENTRY_DSN") or "")
    match = re.search(r"/(\d+)$", dsn.strip())
    if match:
        return "react-native"
    return "react-native"


def check_sentry_recent_issues(
    *,
    env: dict[str, str],
    limit: int = 5,
    warning_threshold: int = 10,
    critical_threshold: int = 20,
    timeout_seconds: float = 10,
) -> tuple[str, str]:
    token = str(env.get("SENTRY_AUTH_TOKEN") or env.get("SENTRY_API_TOKEN") or "").strip()
    org = _sentry_org_slug(env)
    project = _sentry_project_slug(env)
    if not token:
        return "skipped", "Sentry check skipped until SENTRY_AUTH_TOKEN is available"
    url = (
        f"https://sentry.io/api/0/projects/{org}/{project}/issues/"
        f"?query=is:unresolved&limit={max(1, limit)}"
    )
    request = Request(
        url,
        method="GET",
        headers={
            "Authorization": f"Bearer {token}",
            "User-Agent": "Axon-Watch-DashPro-Monitor/1.0",
        },
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            status = int(response.status)
            body = response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        status = int(exc.code)
        body = exc.read().decode("utf-8", errors="replace")
    except (TimeoutError, URLError, OSError) as exc:
        return "critical", f"Sentry API query failed: {exc}"

    if status == 401:
        return "critical", "Sentry API rejected the auth token"
    if status == 403:
        return "warning", "Sentry token lacks issue read scope"
    if status != 200:
        return "critical", f"Sentry API HTTP {status}: {body[:200]}"

    try:
        issues = json.loads(body)
    except json.JSONDecodeError:
        return "critical", "Sentry API returned non-JSON payload"
    if not isinstance(issues, list):
        return "critical", "Sentry API response was not an issue list"
    if not issues:
        return "ok", f"Sentry project {project} has zero unresolved issues"

    titles = [str(item.get("title") or "unknown")[:80] for item in issues[:3] if isinstance(item, dict)]
    total_events = sum(int(item.get("count") or 0) for item in issues if isinstance(item, dict))
    detail = (
        f"Sentry returned {len(issues)} unresolved issue(s), {total_events} event(s); "
        f"latest={titles[0] if titles else 'unknown'}"
    )
    if len(issues) >= critical_threshold or total_events >= critical_threshold * 5:
        return "critical", detail
    if len(issues) >= warning_threshold:
        return "warning", detail
    return "ok", detail
