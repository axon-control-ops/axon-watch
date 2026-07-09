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


def fetch_watch_inbox(timeout_seconds: float = 5.0) -> dict[str, object] | None:
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


def fetch_watch_summary(timeout_seconds: float = 5.0) -> dict[str, object] | None:
    url = f"{watch_base_url()}/internal/watch/summary"

    try:
        request = Request(url, headers={"Accept": "application/json"})
        with urlopen(request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (URLError, TimeoutError, json.JSONDecodeError, OSError, ValueError):
        return None

    if not isinstance(payload, dict):
        return None
    return payload


def fetch_watch_monitors(timeout_seconds: float = 5.0) -> dict[str, object] | None:
    url = f"{watch_base_url()}/internal/watch/monitors"

    try:
        request = Request(url, headers={"Accept": "application/json"})
        with urlopen(request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (URLError, TimeoutError, json.JSONDecodeError, OSError, ValueError):
        return None

    if not isinstance(payload, dict):
        return None
    return payload


def fetch_watch_connectors(timeout_seconds: float = 5.0) -> dict[str, object] | None:
    url = f"{watch_base_url()}/internal/watch/connectors"

    try:
        request = Request(url, headers={"Accept": "application/json"})
        with urlopen(request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (URLError, TimeoutError, json.JSONDecodeError, OSError, ValueError):
        return None

    if not isinstance(payload, dict):
        return None
    return payload


def fetch_watch_tunnel(timeout_seconds: float = 1.0) -> dict[str, object] | None:
    url = f"{watch_base_url()}/internal/watch/tunnel"

    try:
        request = Request(url, headers={"Accept": "application/json"})
        with urlopen(request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (URLError, TimeoutError, json.JSONDecodeError, OSError, ValueError):
        return None

    if not isinstance(payload, dict):
        return None
    return payload


def post_watch_tunnel_action(action: str, timeout_seconds: float = 90.0) -> dict[str, object] | None:
    normalized = action.strip().lower()
    if normalized not in {"start", "stop"}:
        return None
    url = f"{watch_base_url()}/internal/watch/tunnel/{normalized}"

    try:
        request = Request(
            url,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            method="POST",
            data=b"{}",
        )
        with urlopen(request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (URLError, TimeoutError, json.JSONDecodeError, OSError, ValueError):
        return None

    if not isinstance(payload, dict):
        return None
    return payload


def post_watch_command(body: dict[str, object], timeout_seconds: float = 2.0) -> dict[str, object] | None:
    url = f"{watch_base_url()}/internal/watch/commands"
    encoded = json.dumps(body).encode("utf-8")

    try:
        request = Request(
            url,
            data=encoded,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (URLError, TimeoutError, json.JSONDecodeError, OSError, ValueError):
        return None

    if not isinstance(payload, dict):
        return None
    return payload


def get_watch_command(command_id: str, timeout_seconds: float = 1.0) -> dict[str, object] | None:
    url = f"{watch_base_url()}/internal/watch/commands/{command_id.strip()}"

    try:
        request = Request(url, headers={"Accept": "application/json"})
        with urlopen(request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (URLError, TimeoutError, json.JSONDecodeError, OSError, ValueError):
        return None

    if not isinstance(payload, dict):
        return None
    return payload


def fetch_watch_events(
    *,
    limit: int = 20,
    cursor: str = "",
    timeout_seconds: float = 1.0,
) -> dict[str, object] | None:
    query = f"limit={max(1, min(100, int(limit)))}"
    if cursor.strip():
        query = f"{query}&cursor={cursor.strip()}"
    url = f"{watch_base_url()}/internal/watch/events?{query}"

    try:
        request = Request(url, headers={"Accept": "application/json"})
        with urlopen(request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (URLError, TimeoutError, json.JSONDecodeError, OSError, ValueError):
        return None

    if not isinstance(payload, dict):
        return None
    return payload


def fetch_watch_delivery_receipts(
    *,
    limit: int = 20,
    cursor: str = "",
    timeout_seconds: float = 1.0,
) -> dict[str, object] | None:
    query = f"limit={max(1, min(100, int(limit)))}"
    if cursor.strip():
        query = f"{query}&cursor={cursor.strip()}"
    url = f"{watch_base_url()}/internal/watch/delivery/receipts?{query}"

    try:
        request = Request(url, headers={"Accept": "application/json"})
        with urlopen(request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (URLError, TimeoutError, json.JSONDecodeError, OSError, ValueError):
        return None

    if not isinstance(payload, dict):
        return None
    return payload
