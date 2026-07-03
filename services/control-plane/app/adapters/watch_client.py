"""Lightweight watch-service HTTP adapter for control-plane projections."""

from __future__ import annotations

import json
import os
from urllib.error import URLError
from urllib.request import Request, urlopen


def watch_base_url() -> str:
    return os.environ.get(
        "AXON_WATCH_WATCH_SERVICE_BASE_URL",
        "http://127.0.0.1:8788",
    ).rstrip("/")


def fetch_watch_inbox(timeout_seconds: float = 0.5) -> dict[str, object] | None:
    url = f"{watch_base_url()}/internal/watch/inbox"

    try:
        request = Request(url, headers={"Accept": "application/json"})
        with urlopen(request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (URLError, TimeoutError, json.JSONDecodeError, OSError, ValueError):
        return None

    if not isinstance(payload, dict):
        return None
    return payload
