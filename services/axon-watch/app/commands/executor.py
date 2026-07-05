"""Execute bounded watch commands."""

from __future__ import annotations

from app.connectors.catalog import load_watch_connector_definitions
from app.connectors.probe import probe_connector
from app.watch_summary import build_watch_summary


class WatchCommandError(ValueError):
    pass


def execute_reprobe_connector(*, connector_id: str) -> dict[str, object]:
    normalized_id = connector_id.strip()
    if not normalized_id:
        raise WatchCommandError("target_id is required for reprobe_connector")

    definitions = load_watch_connector_definitions()
    definition = definitions.get(normalized_id)
    if definition is None:
        raise WatchCommandError(f"connector not found: {normalized_id}")

    record = probe_connector(definition)
    return {
        "connector_id": normalized_id,
        "connector_status": record.get("status"),
        "detail": record.get("detail", ""),
        "latency_ms": record.get("latency_ms"),
        "last_checked_at": record.get("last_checked_at"),
    }


def execute_refresh_summary() -> dict[str, object]:
    summary = build_watch_summary()
    return {
        "summary_status": summary.get("status"),
        "connectors_ok": summary.get("connectors", {}).get("ok"),
        "updated_at": summary.get("updated_at"),
    }


def execute_watch_command(record: dict[str, object]) -> dict[str, object]:
    command_type = str(record.get("command_type", "")).strip()
    if command_type == "reprobe_connector":
        return execute_reprobe_connector(connector_id=str(record.get("target_id", "")))
    if command_type == "refresh_summary":
        return execute_refresh_summary()
    raise WatchCommandError(f"unsupported command_type: {command_type}")
