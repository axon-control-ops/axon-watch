"""Lightweight watch-service HTTP adapter for control-plane projections."""

from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def watch_base_url() -> str:
    return os.environ.get(
        "AXON_WATCH_WATCH_SERVICE_BASE_URL",
        "http://127.0.0.1:8788",
    ).rstrip("/")


def fetch_watch_inbox(timeout_seconds: float = 10.0) -> dict[str, object] | None:
    """Fetch watch inbox.

    Native IMAP + monitor probes regularly exceed 1.5s on cache miss, so the
    default timeout must cover a cold poll without projecting a false empty inbox.
    """

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


def fetch_watch_summary(timeout_seconds: float = 1.5) -> dict[str, object] | None:
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


def _parse_watch_error_payload(exc: BaseException) -> dict[str, object] | None:
    if not isinstance(exc, HTTPError):
        return None
    try:
        raw = exc.read().decode("utf-8", errors="replace")
        parsed = json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, OSError, ValueError):
        return {"ok": False, "reason": "http_error", "status_code": int(exc.code)}
    if isinstance(parsed, dict) and isinstance(parsed.get("detail"), dict):
        return parsed["detail"]
    if isinstance(parsed, dict):
        return parsed
    return {"ok": False, "reason": "http_error", "status_code": int(exc.code), "detail": str(parsed)}


def post_watch_sentry_issue_resolve(
    issue_id: str,
    *,
    status: str = "resolved",
    requested_by: str = "operator",
    timeout_seconds: float = 20.0,
) -> dict[str, object] | None:
    normalized = str(issue_id or "").strip()
    if not normalized:
        return {"ok": False, "reason": "missing_issue_id"}
    url = f"{watch_base_url()}/internal/watch/sentry/issues/{normalized}/resolve"
    encoded = json.dumps(
        {
            "status": str(status or "resolved").strip() or "resolved",
            "requested_by": str(requested_by or "operator").strip() or "operator",
        }
    ).encode("utf-8")

    try:
        request = Request(
            url,
            data=encoded,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError, ValueError) as exc:
        error_payload = _parse_watch_error_payload(exc)
        if error_payload is not None:
            return error_payload
        return None

    if not isinstance(payload, dict):
        return None
    return payload


def post_watch_sentry_probe_write(timeout_seconds: float = 15.0) -> dict[str, object] | None:
    url = f"{watch_base_url()}/internal/watch/sentry/probe-write"

    try:
        request = Request(
            url,
            data=b"{}",
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError, ValueError) as exc:
        error_payload = _parse_watch_error_payload(exc)
        if error_payload is not None:
            return error_payload
        return None

    if not isinstance(payload, dict):
        return None
    return payload
