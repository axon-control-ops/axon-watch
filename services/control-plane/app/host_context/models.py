"""Canonical host-context DTO helpers (normalized dict records)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def normalize_snapshot(raw: dict[str, Any], *, device_id: str) -> dict[str, Any]:
    generated_at = str(raw.get("generated_at") or utc_now_iso())
    host = raw.get("host") if isinstance(raw.get("host"), dict) else {}
    media = raw.get("media") if isinstance(raw.get("media"), dict) else {}
    windows = raw.get("windows") if isinstance(raw.get("windows"), list) else []
    health = raw.get("health") if isinstance(raw.get("health"), dict) else {}
    return {
        "snapshot_id": str(raw.get("snapshot_id") or new_id("hsnap")),
        "device_id": device_id,
        "generated_at": generated_at,
        "host": {
            "hostname": str(host.get("hostname") or ""),
            "platform": str(host.get("platform") or ""),
            "platform_release": str(host.get("platform_release") or ""),
            "machine": str(host.get("machine") or ""),
            "user": str(host.get("user") or ""),
        },
        "health": {
            "cpu_percent": _optional_float(health.get("cpu_percent")),
            "memory_percent": _optional_float(health.get("memory_percent")),
            "battery_percent": _optional_float(health.get("battery_percent")),
            "on_ac": health.get("on_ac"),
        },
        "media": {
            "playing": bool(media.get("playing", False)),
            "title": str(media.get("title") or ""),
            "artist": str(media.get("artist") or ""),
            "app": str(media.get("app") or ""),
        },
        "windows": [
            {
                "window_id": str(item.get("window_id") or ""),
                "title": str(item.get("title") or ""),
                "app": str(item.get("app") or ""),
                "focused": bool(item.get("focused", False)),
            }
            for item in windows
            if isinstance(item, dict)
        ][:40],
        "capabilities": [
            str(item)
            for item in (raw.get("capabilities") if isinstance(raw.get("capabilities"), list) else [])
            if str(item).strip()
        ],
    }


def normalize_artifact(raw: dict[str, Any], *, device_id: str) -> dict[str, Any]:
    return {
        "artifact_id": str(raw.get("artifact_id") or new_id("hart")),
        "device_id": device_id,
        "path": str(raw.get("path") or ""),
        "title": str(raw.get("title") or raw.get("name") or ""),
        "kind": str(raw.get("kind") or "file"),
        "mime_type": str(raw.get("mime_type") or ""),
        "origin": str(raw.get("origin") or "allowlist"),
        "sensitivity": str(raw.get("sensitivity") or "normal"),
        "modified_at": str(raw.get("modified_at") or utc_now_iso()),
        "size_bytes": int(raw.get("size_bytes") or 0),
        "thumbnail_local": bool(raw.get("thumbnail_local", False)),
        "workspace_id": str(raw.get("workspace_id") or ""),
        "meta": raw.get("meta") if isinstance(raw.get("meta"), dict) else {},
    }


def normalize_event(raw: dict[str, Any], *, device_id: str) -> dict[str, Any]:
    return {
        "event_id": str(raw.get("event_id") or new_id("hevt")),
        "device_id": device_id,
        "kind": str(raw.get("kind") or "host.event"),
        "title": str(raw.get("title") or ""),
        "detail": str(raw.get("detail") or ""),
        "occurred_at": str(raw.get("occurred_at") or utc_now_iso()),
        "artifact_id": str(raw.get("artifact_id") or ""),
        "sensitivity": str(raw.get("sensitivity") or "normal"),
        "meta": raw.get("meta") if isinstance(raw.get("meta"), dict) else {},
    }


def normalize_receipt(raw: dict[str, Any], *, device_id: str) -> dict[str, Any]:
    return {
        "receipt_id": str(raw.get("receipt_id") or new_id("hrcpt")),
        "device_id": device_id,
        "command_id": str(raw.get("command_id") or ""),
        "action": str(raw.get("action") or ""),
        "tier": str(raw.get("tier") or "auto"),
        "status": str(raw.get("status") or "ok"),
        "result_summary": str(raw.get("result_summary") or ""),
        "created_at": str(raw.get("created_at") or utc_now_iso()),
        "meta": raw.get("meta") if isinstance(raw.get("meta"), dict) else {},
    }


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
