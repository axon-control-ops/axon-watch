"""Lightweight watch-service HTTP adapter for control-plane projections."""

from __future__ import annotations

import copy
import json
import os
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request

from app.adapters.watch_http import watch_base_url, watch_request_headers, watch_urlopen, watch_urlopen

# Boot stampede protection: /api/agents, /api/workspaces, /api/inbox, fleet-health,
# and runtime/summary all share this fetch. Without SWR + single-flight, one cold
# watch probe (up to 25s) stacks N blocked worker threads and starves the UI.
_INBOX_CACHE_TTL_SECONDS = 5.0
_INBOX_CACHE: dict[str, object] = {"fetched_at": 0.0, "payload": None}
_INBOX_CACHE_LOCK = threading.Lock()
_INBOX_BUILD_LOCK = threading.Lock()
_INBOX_BACKGROUND_REFRESHING = False

# Re-export for callers that import watch_base_url from this module.
__all__ = ("watch_base_url", "reset_watch_inbox_cache")


def reset_watch_inbox_cache() -> None:
    """Test helper: drop cached inbox so the next fetch is cold."""
    global _INBOX_BACKGROUND_REFRESHING
    with _INBOX_CACHE_LOCK:
        _INBOX_CACHE["fetched_at"] = 0.0
        _INBOX_CACHE["payload"] = None
        _INBOX_BACKGROUND_REFRESHING = False


def _inbox_cache_fresh(fetched_at: float, now: float, payload: object) -> bool:
    return (
        payload is not None
        and isinstance(payload, dict)
        and (now - fetched_at) < _INBOX_CACHE_TTL_SECONDS
    )


def _store_watch_inbox_cache(payload: dict[str, object]) -> None:
    with _INBOX_CACHE_LOCK:
        _INBOX_CACHE["fetched_at"] = time.monotonic()
        _INBOX_CACHE["payload"] = copy.deepcopy(payload)


def _read_watch_inbox_cache() -> tuple[float, dict[str, object] | None]:
    with _INBOX_CACHE_LOCK:
        payload = _INBOX_CACHE.get("payload")
        fetched_at = float(_INBOX_CACHE.get("fetched_at") or 0.0)
        if isinstance(payload, dict):
            return fetched_at, copy.deepcopy(payload)
        return fetched_at, None


def _fetch_watch_inbox_uncached(
    timeout_seconds: float,
    *,
    force: bool = False,
) -> dict[str, object] | None:
    url = f"{watch_base_url()}/internal/watch/inbox"
    if force:
        url += "?force=true"

    try:
        request = Request(url, headers=watch_request_headers())
        with watch_urlopen(request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (URLError, TimeoutError, json.JSONDecodeError, OSError, ValueError):
        return None

    if not isinstance(payload, dict):
        return None
    return payload


def _start_background_inbox_refresh(timeout_seconds: float) -> None:
    global _INBOX_BACKGROUND_REFRESHING

    def _refresh() -> None:
        global _INBOX_BACKGROUND_REFRESHING
        try:
            payload = _fetch_watch_inbox_uncached(timeout_seconds)
            if payload is not None:
                _store_watch_inbox_cache(payload)
        finally:
            with _INBOX_CACHE_LOCK:
                _INBOX_BACKGROUND_REFRESHING = False

    thread = threading.Thread(
        target=_refresh,
        name="cp-watch-inbox-refresh",
        daemon=True,
    )
    thread.start()


def _schedule_inbox_refresh_if_idle(timeout_seconds: float) -> bool:
    global _INBOX_BACKGROUND_REFRESHING
    with _INBOX_CACHE_LOCK:
        should_refresh = not _INBOX_BACKGROUND_REFRESHING
        if should_refresh:
            _INBOX_BACKGROUND_REFRESHING = True
    if should_refresh:
        _start_background_inbox_refresh(timeout_seconds)
    return should_refresh


def fetch_watch_inbox(
    timeout_seconds: float = 25.0,
    *,
    allow_stale: bool = True,
    force_refresh: bool = False,
    cached_only: bool = False,
) -> dict[str, object] | None:
    """Fetch watch inbox with SWR + single-flight.

    Cold monitor/IMAP probes regularly take 8–15s after a restart, so the
    default timeout must cover a cold poll without projecting a false empty inbox.
    Concurrent boot callers must share one in-flight probe and reuse a short TTL
    cache so /api/agents is not starved behind N×25s urlopen waits.

    ``cached_only=True`` never blocks on a live probe (used by workspace/agent
    catalog enrichment so a cold inbox cannot stall the operator shell).
    """

    now = time.monotonic()
    fetched_at, cached = _read_watch_inbox_cache()
    if not force_refresh and _inbox_cache_fresh(fetched_at, now, cached):
        return cached

    if cached_only:
        _schedule_inbox_refresh_if_idle(timeout_seconds)
        return cached

    if allow_stale and not force_refresh and cached is not None:
        _schedule_inbox_refresh_if_idle(timeout_seconds)
        return cached

    # Cold path: single-flight so concurrent boot callers share one urlopen.
    # Catalog callers use cached_only=True and never reach here.
    lock_acquired = _INBOX_BUILD_LOCK.acquire(timeout=timeout_seconds)
    if not lock_acquired:
        fetched_at, cached = _read_watch_inbox_cache()
        if cached is not None:
            return cached
        return None

    try:
        now = time.monotonic()
        fetched_at, cached = _read_watch_inbox_cache()
        if not force_refresh and _inbox_cache_fresh(fetched_at, now, cached):
            return cached
        if allow_stale and not force_refresh and cached is not None:
            _schedule_inbox_refresh_if_idle(timeout_seconds)
            return cached

        payload = _fetch_watch_inbox_uncached(timeout_seconds, force=force_refresh)
        if payload is not None:
            _store_watch_inbox_cache(payload)
            return payload
        # Prefer last good snapshot over projecting a false empty/unavailable inbox.
        if cached is not None:
            return cached
        return None
    finally:
        _INBOX_BUILD_LOCK.release()


def fetch_watch_summary(timeout_seconds: float = 1.5) -> dict[str, object] | None:
    url = f"{watch_base_url()}/internal/watch/summary"

    try:
        request = Request(url, headers=watch_request_headers())
        with watch_urlopen(request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (URLError, TimeoutError, json.JSONDecodeError, OSError, ValueError):
        return None

    if not isinstance(payload, dict):
        return None
    return payload


def fetch_watch_monitors(timeout_seconds: float = 5.0) -> dict[str, object] | None:
    url = f"{watch_base_url()}/internal/watch/monitors"

    try:
        request = Request(url, headers=watch_request_headers())
        with watch_urlopen(request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (URLError, TimeoutError, json.JSONDecodeError, OSError, ValueError):
        return None

    if not isinstance(payload, dict):
        return None
    return payload


def fetch_watch_connectors(timeout_seconds: float = 5.0) -> dict[str, object] | None:
    url = f"{watch_base_url()}/internal/watch/connectors"

    try:
        request = Request(url, headers=watch_request_headers())
        with watch_urlopen(request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (URLError, TimeoutError, json.JSONDecodeError, OSError, ValueError):
        return None

    if not isinstance(payload, dict):
        return None
    return payload


def fetch_watch_tunnel(timeout_seconds: float = 1.0) -> dict[str, object] | None:
    url = f"{watch_base_url()}/internal/watch/tunnel"

    try:
        request = Request(url, headers=watch_request_headers())
        with watch_urlopen(request, timeout=timeout_seconds) as response:
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
            headers=watch_request_headers(content_type="application/json"),
            method="POST",
            data=b"{}",
        )
        with watch_urlopen(request, timeout=timeout_seconds) as response:
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
            headers=watch_request_headers(content_type="application/json"),
            method="POST",
        )
        with watch_urlopen(request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (URLError, TimeoutError, json.JSONDecodeError, OSError, ValueError):
        return None

    if not isinstance(payload, dict):
        return None
    return payload


def get_watch_command(command_id: str, timeout_seconds: float = 1.0) -> dict[str, object] | None:
    url = f"{watch_base_url()}/internal/watch/commands/{command_id.strip()}"

    try:
        request = Request(url, headers=watch_request_headers())
        with watch_urlopen(request, timeout=timeout_seconds) as response:
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
        request = Request(url, headers=watch_request_headers())
        with watch_urlopen(request, timeout=timeout_seconds) as response:
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
        request = Request(url, headers=watch_request_headers())
        with watch_urlopen(request, timeout=timeout_seconds) as response:
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
            headers=watch_request_headers(content_type="application/json"),
            method="POST",
        )
        with watch_urlopen(request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError, ValueError) as exc:
        error_payload = _parse_watch_error_payload(exc)
        if error_payload is not None:
            return error_payload
        return None

    if not isinstance(payload, dict):
        return None
    return payload


def post_watch_sentry_issue_attend(
    issue_id: str,
    *,
    confirm_release: str = "",
    requested_by: str = "operator",
    mark_resolved_in_next_release: bool = True,
    workspace_id: str = "workspace_dashpro",
    timeout_seconds: float = 20.0,
) -> dict[str, object] | None:
    normalized = str(issue_id or "").strip()
    if not normalized:
        return {"ok": False, "reason": "missing_issue_id"}
    url = f"{watch_base_url()}/internal/watch/sentry/issues/{normalized}/attend"
    encoded = json.dumps(
        {
            "confirm_release": str(confirm_release or "").strip(),
            "requested_by": str(requested_by or "operator").strip() or "operator",
            "mark_resolved_in_next_release": bool(mark_resolved_in_next_release),
            "workspace_id": str(workspace_id or "workspace_dashpro").strip()
            or "workspace_dashpro",
        }
    ).encode("utf-8")

    try:
        request = Request(
            url,
            data=encoded,
            headers=watch_request_headers(content_type="application/json"),
            method="POST",
        )
        with watch_urlopen(request, timeout=timeout_seconds) as response:
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
            headers=watch_request_headers(content_type="application/json"),
            method="POST",
        )
        with watch_urlopen(request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError, ValueError) as exc:
        error_payload = _parse_watch_error_payload(exc)
        if error_payload is not None:
            return error_payload
        return None

    if not isinstance(payload, dict):
        return None
    return payload


def fetch_watch_email_folders(
    account_id: str,
    timeout_seconds: float = 15.0,
) -> dict[str, object] | None:
    query = urlencode({"account_id": account_id})
    url = f"{watch_base_url()}/internal/watch/email/folders?{query}"

    try:
        request = Request(url, headers=watch_request_headers())
        with watch_urlopen(request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError, ValueError):
        return None

    if not isinstance(payload, dict):
        return None
    return payload


def fetch_watch_email_messages(
    account_id: str,
    role: str = "inbox",
    *,
    limit: int = 25,
    timeout_seconds: float = 20.0,
) -> dict[str, object] | None:
    query = urlencode({"account_id": account_id, "role": role, "limit": limit})
    url = f"{watch_base_url()}/internal/watch/email/messages?{query}"

    try:
        request = Request(url, headers=watch_request_headers())
        with watch_urlopen(request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError, ValueError):
        return None

    if not isinstance(payload, dict):
        return None
    return payload
