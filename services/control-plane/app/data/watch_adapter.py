"""Proxy operator data snapshot from axon-watch internal APIs."""

from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request

from app.adapters.watch_http import watch_request_headers, watch_urlopen

from app.adapters.watch_client import watch_base_url


def _request_json(
    method: str,
    path: str,
    *,
    timeout_seconds: float = 10,
) -> dict[str, Any]:
    url = f"{watch_base_url()}{path}"
    request = Request(url, method=method, headers=watch_request_headers())
    try:
        with watch_urlopen(request, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"watch data API HTTP {exc.code}: {body[:200]}") from exc
    except (TimeoutError, URLError, OSError) as exc:
        raise RuntimeError(f"watch data API unavailable: {exc}") from exc

    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError("watch data API returned non-JSON payload") from exc
    if not isinstance(parsed, dict):
        raise RuntimeError("watch data API response was not an object")
    return parsed


def fetch_watch_data_snapshot(*, limit: int = 50) -> dict[str, Any]:
    max_limit = max(1, min(100, int(limit or 50)))
    payload = _request_json("GET", f"/internal/watch/data/snapshot?limit={max_limit}")
    data = payload.get("data")
    if not isinstance(data, dict):
        raise RuntimeError("watch data snapshot missing data object")
    return data
