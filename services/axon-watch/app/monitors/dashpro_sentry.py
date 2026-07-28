"""DashPro Sentry monitor check (bounded port of axon-local slice)."""

from __future__ import annotations

import json
import os
import re
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from app.monitors.sentry_issue_sample import extract_sentry_issue_sample
from app.signals.sentry_issue_attendance_store import (
    attendance_map,
    should_suppress_issue,
)


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


def _sentry_issue_query(*, environment: str | None = None) -> str:
    env_name = str(
        environment
        if environment is not None
        else os.environ.get("AXON_WATCH_SENTRY_ENVIRONMENT")
        or "production"
    ).strip()
    if not env_name or env_name.lower() in {"*", "all", "any"}:
        return "is:unresolved"
    return f"is:unresolved environment:{env_name}"


def check_sentry_recent_issues(
    *,
    env: dict[str, str],
    limit: int = 5,
    warning_threshold: int = 10,
    critical_threshold: int = 20,
    timeout_seconds: float = 10,
    environment: str | None = None,
    workspace_id: str = "workspace_dashpro",
) -> tuple[str, str, list[dict[str, object]]]:
    token = str(env.get("SENTRY_AUTH_TOKEN") or env.get("SENTRY_API_TOKEN") or "").strip()
    org = _sentry_org_slug(env)
    project = _sentry_project_slug(env)
    empty: list[dict[str, object]] = []
    if not token:
        return "skipped", "Sentry check skipped until SENTRY_AUTH_TOKEN is available", empty
    query = _sentry_issue_query(environment=environment)
    url = (
        f"https://sentry.io/api/0/projects/{org}/{project}/issues/"
        f"?query={quote(query)}&limit={max(1, limit)}"
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
        # Transient network blips stay warning (not critical) so inbox severity
        # can keep them below Attention thresholds via the shared marker.
        return "warning", f"Sentry API query failed: {exc}", empty

    if status == 401:
        return "critical", "Sentry API rejected the auth token", empty
    if status == 403:
        return "warning", "Sentry token lacks issue read scope", empty
    if status != 200:
        return "critical", f"Sentry API HTTP {status}: {body[:200]}", empty

    try:
        issues = json.loads(body)
    except json.JSONDecodeError:
        return "critical", "Sentry API returned non-JSON payload", empty
    if not isinstance(issues, list):
        return "critical", "Sentry API response was not an issue list", empty
    if not issues:
        return "ok", f"Sentry project {project} has zero unresolved production issues", empty

    sample = extract_sentry_issue_sample(issues, limit=max(1, limit * 2))
    attendances = attendance_map(workspace_id=workspace_id)
    active_sample: list[dict[str, object]] = []
    suppressed = 0
    for item in sample:
        attendance = attendances.get(str(item.get("id") or ""))
        if should_suppress_issue(item, attendance):
            suppressed += 1
            continue
        active_sample.append(item)
        if len(active_sample) >= max(1, limit):
            break

    if not active_sample:
        detail = (
            f"Sentry production issues attended after OTA/build "
            f"({suppressed} suppressed); no active unresolved noise"
        )
        return "ok", detail, empty

    titles = [str(item.get("title") or "unknown")[:80] for item in active_sample[:3]]
    total_events = sum(int(item.get("count") or 0) for item in active_sample)
    detail = (
        f"Sentry returned {len(active_sample)} unresolved production issue(s), "
        f"{total_events} event(s)"
    )
    if suppressed:
        detail += f", {suppressed} attended/suppressed"
    detail += f"; latest={titles[0] if titles else 'unknown'}"
    if len(active_sample) >= critical_threshold or total_events >= critical_threshold * 5:
        return "critical", detail, active_sample
    if len(active_sample) >= warning_threshold:
        return "warning", detail, active_sample
    return "ok", detail, active_sample
