"""In-memory device enrollment store (scaffold; swap for durable store later)."""

from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from typing import Any


class DeviceEnrollmentError(ValueError):
    """Domain error for enrollment / revocation."""


_LOCK = threading.RLock()
_DEVICES: dict[str, dict[str, Any]] = {}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def reset_store() -> None:
    with _LOCK:
        _DEVICES.clear()


def enroll(
    *,
    label: str,
    platform: str = "android",
    capabilities: list[str] | None = None,
    device_id: str | None = None,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cleaned_label = (label or "").strip()
    if not cleaned_label:
        raise DeviceEnrollmentError("label is required")
    cleaned_platform = (platform or "android").strip() or "android"
    caps = [str(c).strip() for c in (capabilities or []) if str(c).strip()]
    requested_id = (device_id or "").strip()
    with _LOCK:
        if requested_id and requested_id in _DEVICES:
            existing = _DEVICES[requested_id]
            if existing.get("status") == "active":
                # Idempotent re-enroll refreshes label/caps.
                existing["label"] = cleaned_label
                existing["platform"] = cleaned_platform
                existing["capabilities"] = caps
                if meta:
                    existing["meta"] = {**existing.get("meta", {}), **meta}
                existing["revoked_at"] = None
                return dict(existing)
            # Re-activate a previously revoked id.
            existing.update(
                {
                    "label": cleaned_label,
                    "platform": cleaned_platform,
                    "capabilities": caps,
                    "status": "active",
                    "enrolled_at": _now(),
                    "revoked_at": None,
                    "meta": {**(existing.get("meta") or {}), **(meta or {})},
                }
            )
            return dict(existing)

        new_id = requested_id or f"dev_{uuid.uuid4().hex[:12]}"
        if new_id in _DEVICES:
            raise DeviceEnrollmentError(f"device_id already exists: {new_id}")
        record = {
            "device_id": new_id,
            "label": cleaned_label,
            "platform": cleaned_platform,
            "status": "active",
            "capabilities": caps,
            "enrolled_at": _now(),
            "revoked_at": None,
            "meta": dict(meta or {}),
        }
        _DEVICES[new_id] = record
        return dict(record)


def revoke(device_id: str) -> dict[str, Any]:
    cleaned = (device_id or "").strip()
    if not cleaned:
        raise DeviceEnrollmentError("device_id is required")
    with _LOCK:
        record = _DEVICES.get(cleaned)
        if record is None:
            raise DeviceEnrollmentError(f"device not found: {cleaned}")
        if record.get("status") == "revoked":
            return dict(record)
        record["status"] = "revoked"
        record["revoked_at"] = _now()
        return dict(record)


def get_device(device_id: str) -> dict[str, Any] | None:
    cleaned = (device_id or "").strip()
    with _LOCK:
        record = _DEVICES.get(cleaned)
        return dict(record) if record else None


def list_devices(*, status: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    capped = max(1, min(int(limit), 500))
    wanted = (status or "").strip().lower() or None
    with _LOCK:
        rows = [dict(v) for v in _DEVICES.values()]
    if wanted:
        rows = [r for r in rows if str(r.get("status", "")).lower() == wanted]
    rows.sort(key=lambda r: str(r.get("enrolled_at") or ""), reverse=True)
    return rows[:capped]
