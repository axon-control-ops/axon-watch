"""DashPro PostHog monitor check (bounded port of axon-local slice)."""

from __future__ import annotations

import json
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
    limit: int = 5,
    timeout_seconds: float = 20,
    retries: int = 1,
) -> tuple[str, str]:
    api_key = str(
        env.get("POSTHOG_PERSONAL_API_KEY")
        or env.get("POSTHOG_API_KEY")
        or ""
    ).strip()
    project_id = str(
        env.get("DASHPRO_POSTHOG_PROJECT_ID")
        or env.get("POSTHOG_PROJECT_ID")
        or ""
    ).strip()
    if not api_key:
        return "skipped", "PostHog check skipped until POSTHOG_PERSONAL_API_KEY is available"
    if not project_id:
        return "skipped", "PostHog check skipped until DASHPRO_POSTHOG_PROJECT_ID is available"

    url = f"{_posthog_api_base(env)}/projects/{project_id}/events/?limit={max(1, limit)}"
    request = Request(
        url,
        method="GET",
        headers={
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "Axon-Watch-DashPro-Monitor/1.0",
        },
    )
    attempts = max(1, int(retries) + 1)
    timeout = max(1.0, float(timeout_seconds))
    status = 0
    body = ""
    last_exc: Exception | None = None
    for attempt in range(attempts):
        try:
            with urlopen(request, timeout=timeout) as response:
                status = int(response.status)
                body = response.read().decode("utf-8", errors="replace")
            last_exc = None
            break
        except HTTPError as exc:
            status = int(exc.code)
            body = exc.read().decode("utf-8", errors="replace")
            last_exc = None
            break
        except (TimeoutError, URLError, OSError) as exc:
            last_exc = exc
            if attempt + 1 < attempts:
                continue
            # Transient network blips stay warning (not critical) so inbox severity
            # can keep them below Attention thresholds via the shared marker.
            return "warning", f"PostHog API query failed: {exc}"

    if last_exc is not None:
        return "warning", f"PostHog API query failed: {last_exc}"

    if status == 401:
        return "critical", "PostHog API rejected the personal API key"
    if status == 403:
        return "critical", "PostHog API denied project read access"
    if status != 200:
        return "critical", f"PostHog API HTTP {status}: {body[:200]}"

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return "critical", "PostHog API returned non-JSON payload"

    results = payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(results, list):
        return "critical", "PostHog API response missing results list"
    if not results:
        return "warning", "PostHog project is reachable but returned zero recent events"

    latest = results[0] if results else {}
    event_name = str((latest.get("event") if isinstance(latest, dict) else "") or "unknown")
    return "ok", f"PostHog returned {len(results)} recent event(s); latest={event_name}"
