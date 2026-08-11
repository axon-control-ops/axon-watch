"""Best-effort Cursor model-quota usage probe (Auto + Composer / API pools)."""

from __future__ import annotations

from contextlib import closing
import json
import os
import sqlite3
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

StatusRecord = dict[str, Any]

_USAGE_CACHE: dict[str, Any] = {"fetched_at": 0.0, "payload": None}
_USAGE_CACHE_TTL_SECONDS = 45.0
_USAGE_LOCK = threading.Lock()
_USAGE_URL = "https://api2.cursor.sh/aiserver.v1.DashboardService/GetCurrentPeriodUsage"
_STRIPE_URL = "https://api2.cursor.sh/auth/full_stripe_profile"


def _utc_now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _state_db_path() -> Path | None:
    override = str(os.environ.get("AXON_WATCH_CURSOR_STATE_DB", "")).strip()
    if override:
        path = Path(override).expanduser()
        return path if path.is_file() else None
    candidates = [
        Path.home() / ".config" / "Cursor" / "User" / "globalStorage" / "state.vscdb",
        Path.home() / ".config" / "cursor" / "User" / "globalStorage" / "state.vscdb",
    ]
    for path in candidates:
        if path.is_file():
            return path
    return None


def _read_cursor_auth_item(key: str) -> str | None:
    db_path = _state_db_path()
    if db_path is None:
        return None
    try:
        with closing(sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)) as connection:
            row = connection.execute(
                "SELECT value FROM ItemTable WHERE key = ?",
                (key,),
            ).fetchone()
    except Exception:
        return None
    if not row:
        return None
    value = row[0]
    if isinstance(value, bytes):
        try:
            value = value.decode("utf-8")
        except Exception:
            return None
    text = str(value or "").strip()
    return text or None


def _http_json(url: str, *, token: str, method: str = "GET", body: bytes | None = None) -> Any:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "User-Agent": "Axon-X-CursorUsageProbe/1.0",
    }
    if method != "GET":
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=12) as response:
        raw = response.read().decode("utf-8", errors="replace")
    return json.loads(raw) if raw.strip() else {}


def _pct(value: object) -> float | None:
    try:
        if value is None or value == "":
            return None
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None


def _empty_usage(*, ok: bool, message: str, source: str = "unavailable") -> StatusRecord:
    return {
        "ok": ok,
        "source": source,
        "updated_at": _utc_now_iso(),
        "membership_type": None,
        "subscription_status": None,
        "on_demand_enabled": None,
        "auto_percent_used": None,
        "api_percent_used": None,
        "total_percent_used": None,
        "display_message": None,
        "auto_display_message": None,
        "api_display_message": None,
        "message": message,
        "allows_agent_retry": True,
    }


def cursor_usage_allows_agent_retry(usage: StatusRecord | None) -> bool:
    """True when Auto headroom or on-demand spend means retries are still sensible."""
    if not isinstance(usage, dict) or not usage.get("ok"):
        # Unknown live quota — do not invent an account-wide hard stop.
        return True
    if usage.get("on_demand_enabled") is True:
        return True
    for key in ("auto_percent_used", "total_percent_used"):
        pct = _pct(usage.get(key))
        if pct is not None and pct < 99.5:
            return True
    return False


def probe_cursor_usage(*, force_refresh: bool = False) -> StatusRecord:
    """Return Cursor pool usage suitable for Runtime status / console indicator."""
    cached = _USAGE_CACHE.get("payload")
    fetched_at = float(_USAGE_CACHE.get("fetched_at") or 0.0)
    if (
        not force_refresh
        and cached is not None
        and (time.monotonic() - fetched_at) < _USAGE_CACHE_TTL_SECONDS
    ):
        return dict(cached)

    with _USAGE_LOCK:
        cached = _USAGE_CACHE.get("payload")
        fetched_at = float(_USAGE_CACHE.get("fetched_at") or 0.0)
        if (
            not force_refresh
            and cached is not None
            and (time.monotonic() - fetched_at) < _USAGE_CACHE_TTL_SECONDS
        ):
            return dict(cached)

        token = _read_cursor_auth_item("cursorAuth/accessToken")
        if not token:
            payload = _empty_usage(
                ok=False,
                message="Cursor session token unavailable on host — open Cursor Settings → Usage.",
            )
            _USAGE_CACHE["fetched_at"] = time.monotonic()
            _USAGE_CACHE["payload"] = dict(payload)
            return dict(payload)

        membership = _read_cursor_auth_item("cursorAuth/stripeMembershipType")
        subscription = _read_cursor_auth_item("cursorAuth/stripeSubscriptionStatus")
        on_demand: bool | None = None
        try:
            stripe = _http_json(_STRIPE_URL, token=token)
            if isinstance(stripe, dict):
                membership = str(stripe.get("membershipType") or membership or "").strip() or membership
                subscription = (
                    str(stripe.get("subscriptionStatus") or subscription or "").strip() or subscription
                )
                if "isOnBillableAuto" in stripe:
                    on_demand = bool(stripe.get("isOnBillableAuto"))
        except Exception:
            pass

        try:
            period = _http_json(_USAGE_URL, token=token, method="POST", body=b"{}")
        except urllib.error.HTTPError as exc:
            payload = _empty_usage(
                ok=False,
                message=f"Cursor usage API returned HTTP {exc.code}.",
            )
            _USAGE_CACHE["fetched_at"] = time.monotonic()
            _USAGE_CACHE["payload"] = dict(payload)
            return dict(payload)
        except Exception as exc:
            payload = _empty_usage(
                ok=False,
                message="Cursor usage probe failed — open Cursor Settings → Usage.",
            )
            _USAGE_CACHE["fetched_at"] = time.monotonic()
            _USAGE_CACHE["payload"] = dict(payload)
            return dict(payload)

        plan = period.get("planUsage") if isinstance(period, dict) else None
        plan = plan if isinstance(plan, dict) else {}
        auto_pct = _pct(plan.get("autoPercentUsed"))
        api_pct = _pct(plan.get("apiPercentUsed"))
        total_pct = _pct(plan.get("totalPercentUsed"))
        payload = {
            "ok": True,
            "source": "cursor_dashboard",
            "updated_at": _utc_now_iso(),
            "membership_type": membership,
            "subscription_status": subscription,
            "on_demand_enabled": on_demand,
            "auto_percent_used": auto_pct,
            "api_percent_used": api_pct,
            "total_percent_used": total_pct,
            "display_message": str(period.get("displayMessage") or "").strip() or None,
            "auto_display_message": str(period.get("autoModelSelectedDisplayMessage") or "").strip()
            or None,
            "api_display_message": str(period.get("namedModelSelectedDisplayMessage") or "").strip()
            or None,
            "message": "Live Cursor usage pools.",
            "allows_agent_retry": True,
        }
        payload["allows_agent_retry"] = cursor_usage_allows_agent_retry(payload)
        _USAGE_CACHE["fetched_at"] = time.monotonic()
        _USAGE_CACHE["payload"] = dict(payload)
        return dict(payload)


__all__ = [
    "cursor_usage_allows_agent_retry",
    "probe_cursor_usage",
]
