"""DashPro PostHog monitor check (bounded port of axon-local slice)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def _posthog_api_base(env: dict[str, str]) -> str:
    host = str(env.get("EXPO_PUBLIC_POSTHOG_HOST") or "https://us.i.posthog.com").strip().lower()
    if "eu.i.posthog.com" in host:
        return "https://eu.posthog.com/api"
    if "us.i.posthog.com" in host:
        return "https://us.posthog.com/api"
    return "https://app.posthog.com/api"


def check_posthog_recent_events(
    *,
    env: dict[str, str],
    hours: int = 24,
    min_events_warning: int = 1,
    timeout_seconds: float = 10,
) -> tuple[str, str]:
    api_key = str(
        env.get("POSTHOG_PERSONAL_API_KEY")
        or env.get("POSTHOG_API_KEY")
        or ""
    ).strip()
    project_id = str(env.get("DASHPRO_POSTHOG_PROJECT_ID") or "").strip()
    if not api_key:
        return "skipped", "PostHog check skipped until POSTHOG_PERSONAL_API_KEY is available"
    if not project_id:
        return "skipped", "PostHog check skipped until DASHPRO_POSTHOG_PROJECT_ID is available"

    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=max(1, hours))
    query = {
        "events": [
            {
                "id": "$pageview",
                "name": "$pageview",
                "type": "events",
                "order": 0,
            }
        ],
        "date_from": start.isoformat(),
        "date_to": end.isoformat(),
    }
    url = f"{_posthog_api_base(env)}/projects/{project_id}/query/"
    request = Request(
        url,
        data=json.dumps({"query": query}).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
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
        return "critical", f"PostHog API query failed: {exc}"

    if status == 401:
        return "critical", "PostHog API rejected the personal API key"
    if status != 200:
        return "critical", f"PostHog API HTTP {status}: {body[:200]}"

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return "critical", "PostHog API returned non-JSON payload"

    results = payload.get("results") if isinstance(payload, dict) else None
    count = len(results) if isinstance(results, list) else 0
    if count < min_events_warning:
        return "warning", f"PostHog returned {count} recent event bucket(s) in the last {hours}h"
    return "ok", f"PostHog returned {count} recent event bucket(s) in the last {hours}h"
