"""DashPro PostHog monitor check (bounded port of axon-local slice)."""

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

_DEFAULT_US_API = "https://us.i.posthog.com/api"
_DEFAULT_EU_API = "https://eu.i.posthog.com/api"
_DEFAULT_APP_API = "https://app.posthog.com/api"


def _normalize_api_base(raw: str) -> str:
    text = str(raw or "").strip().rstrip("/")
    if not text:
        return ""
    if text.endswith("/api"):
        return text
    if text.endswith(".posthog.com") or text.endswith(".i.posthog.com"):
        return f"{text}/api"
    return text


def _posthog_api_base(env: dict[str, str]) -> str:
    override = _normalize_api_base(
        str(env.get("POSTHOG_PERSONAL_API_BASE") or env.get("POSTHOG_API_BASE") or "")
    )
    if override:
        return override

    host = str(env.get("EXPO_PUBLIC_POSTHOG_HOST") or "https://us.i.posthog.com").strip().lower()
    if "eu.i.posthog.com" in host or "eu.posthog.com" in host:
        return _DEFAULT_EU_API
    if "us.i.posthog.com" in host or "us.posthog.com" in host:
        return _DEFAULT_US_API
    return _DEFAULT_APP_API


def _posthog_api_base_candidates(env: dict[str, str]) -> list[str]:
    primary = _posthog_api_base(env)
    host = str(env.get("EXPO_PUBLIC_POSTHOG_HOST") or "").strip().lower()
    region_fallbacks = (
        [_DEFAULT_EU_API, "https://eu.posthog.com/api", _DEFAULT_APP_API]
        if "eu" in host
        else [_DEFAULT_US_API, "https://us.posthog.com/api", _DEFAULT_APP_API]
    )
    candidates: list[str] = []
    for base in [primary, *region_fallbacks]:
        normalized = _normalize_api_base(base)
        if normalized and normalized not in candidates:
            candidates.append(normalized)
    return candidates


def _is_transport_error(exc: Exception) -> bool:
    if isinstance(exc, TimeoutError):
        return True
    if isinstance(exc, URLError):
        return True
    if isinstance(exc, OSError):
        message = str(exc).lower()
        return "name resolution" in message or "temporary failure" in message or exc.errno in (-2, -3)
    return False


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

    path = f"/projects/{project_id}/events/?limit={max(1, limit)}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "User-Agent": "Axon-Watch-DashPro-Monitor/1.0",
    }
    attempts = max(1, int(retries) + 1)
    timeout = max(1.0, float(timeout_seconds))
    api_bases = _posthog_api_base_candidates(env)
    status = 0
    body = ""
    last_exc: Exception | None = None

    for base in api_bases:
        request = Request(f"{base}{path}", method="GET", headers=headers)
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
                if _is_transport_error(exc) and base != api_bases[-1]:
                    break
                return "warning", f"PostHog API query failed: {exc}"
        if last_exc is None:
            break

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
