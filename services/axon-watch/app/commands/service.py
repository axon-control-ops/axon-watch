"""Watch command submission and status retrieval."""

from __future__ import annotations

import uuid
from typing import Any

from app.commands import store as command_store
from app.commands.executor import WatchCommandError, execute_watch_command
from app.events import store as event_store
from app.signals.iso_time import utc_now_iso

_SUPPORTED_COMMAND_TYPES = frozenset({"reprobe_connector", "refresh_summary"})


def _normalize_command_id(raw: str | None) -> str:
    text = str(raw or "").strip()
    return text or f"cmd-{uuid.uuid4().hex[:16]}"


def submit_watch_command(body: dict[str, Any]) -> dict[str, object]:
    command_type = str(body.get("command_type", "")).strip()
    if command_type not in _SUPPORTED_COMMAND_TYPES:
        raise WatchCommandError(f"unsupported command_type: {command_type}")

    command_id = _normalize_command_id(body.get("command_id"))
    existing = command_store.get_command(command_id)
    if existing is not None:
        return {
            "accepted": True,
            "command_id": command_id,
            "status": str(existing.get("status", "")),
            "receipt": existing.get("receipt", {}),
        }

    timestamp = utc_now_iso()
    record: dict[str, object] = {
        "command_id": command_id,
        "command_type": command_type,
        "target_type": str(body.get("target_type", "")).strip(),
        "target_id": str(body.get("target_id", "")).strip(),
        "requested_by": str(body.get("requested_by", "control-plane")).strip() or "control-plane",
        "payload": body.get("payload") if isinstance(body.get("payload"), dict) else {},
        "requested_at": str(body.get("requested_at", "")).strip() or timestamp,
        "status": "accepted",
        "updated_at": timestamp,
        "receipt": {},
    }
    command_store.save_command(record)
    event_store.append_event(
        event_type="command_accepted",
        command_id=command_id,
        payload={"command_type": command_type, "target_id": record["target_id"]},
    )

    try:
        result = execute_watch_command(record)
        completed_at = utc_now_iso()
        receipt = {
            "command_type": command_type,
            "result": result,
            "completed_at": completed_at,
        }
        updated = command_store.update_command(
            command_id,
            status="completed",
            updated_at=completed_at,
            receipt=receipt,
        )
        event_type = (
            "connector_reprobed"
            if command_type == "reprobe_connector"
            else "summary_refreshed"
        )
        event_store.append_event(
            event_type=event_type,
            command_id=command_id,
            payload=result,
        )
        event_store.append_event(
            event_type="command_completed",
            command_id=command_id,
            payload={"status": "completed"},
        )
        assert updated is not None
        return {
            "accepted": True,
            "command_id": command_id,
            "status": "completed",
            "receipt": receipt,
        }
    except WatchCommandError as exc:
        failed_at = utc_now_iso()
        receipt = {
            "command_type": command_type,
            "error": str(exc),
            "completed_at": failed_at,
        }
        command_store.update_command(
            command_id,
            status="failed",
            updated_at=failed_at,
            receipt=receipt,
        )
        event_store.append_event(
            event_type="command_failed",
            command_id=command_id,
            payload={"error": str(exc)},
        )
        return {
            "accepted": False,
            "command_id": command_id,
            "status": "failed",
            "receipt": receipt,
        }


def get_watch_command(command_id: str) -> dict[str, object]:
    record = command_store.get_command(command_id)
    if record is None:
        raise WatchCommandError(f"command not found: {command_id}")
    return {
        "command_id": record["command_id"],
        "command_type": record["command_type"],
        "target_type": record.get("target_type", ""),
        "target_id": record.get("target_id", ""),
        "requested_by": record.get("requested_by", ""),
        "requested_at": record.get("requested_at", ""),
        "status": record.get("status", ""),
        "updated_at": record.get("updated_at", ""),
        "receipt": record.get("receipt", {}),
    }
