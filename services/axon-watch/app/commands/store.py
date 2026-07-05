"""Persisted watch command records for operator-issued observation actions."""

from __future__ import annotations

from copy import deepcopy

_COMMANDS: dict[str, dict[str, object]] = {}


def reset_store() -> None:
    _COMMANDS.clear()


def save_command(record: dict[str, object]) -> dict[str, object]:
    stored = deepcopy(record)
    _COMMANDS[str(stored["command_id"])] = stored
    return deepcopy(stored)


def get_command(command_id: str) -> dict[str, object] | None:
    record = _COMMANDS.get(command_id.strip())
    return deepcopy(record) if record is not None else None


def update_command(command_id: str, **fields: object) -> dict[str, object] | None:
    record = _COMMANDS.get(command_id.strip())
    if record is None:
        return None
    record.update(fields)
    return deepcopy(record)


def latest_command_snapshot() -> dict[str, object]:
    if not _COMMANDS:
        return {
            "last_command_id": "",
            "last_command_status": "",
            "last_command_at": "",
        }

    latest = max(_COMMANDS.values(), key=lambda item: str(item.get("updated_at", "")))
    return {
        "last_command_id": str(latest.get("command_id", "")),
        "last_command_status": str(latest.get("status", "")),
        "last_command_at": str(latest.get("updated_at", "")),
    }
