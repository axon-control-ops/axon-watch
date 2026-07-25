"""Execute bounded watch commands."""

from __future__ import annotations

from app.connectors.catalog import load_watch_connector_definitions
from app.connectors.probe import probe_connector
from app.connectors.summary import reset_connector_probe_cache, store_connector_probe_record
from app.monitors.dashpro_monitor import reset_monitor_probe_cache
from app.signals.suppression_store import acknowledge_signals
from app.tunnel.slice_registry import load_tunnel_slice
from app.tunnel.tunnel_probe import probe_cloudflare_tunnel
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
        tunnel_config = load_tunnel_slice()
        tunnel_id = str((tunnel_config or {}).get("connector_id") or "cloudflare_tunnel").strip()
        if normalized_id == tunnel_id and tunnel_config is not None:
            record = probe_cloudflare_tunnel(tunnel_config)
            store_connector_probe_record(record)
            return {
                "connector_id": normalized_id,
                "connector_status": record.get("status"),
                "detail": record.get("detail", ""),
                "latency_ms": record.get("latency_ms"),
                "last_checked_at": record.get("last_checked_at"),
            }
        raise WatchCommandError(f"connector not found: {normalized_id}")

    record = probe_connector(definition)
    store_connector_probe_record(record)
    return {
        "connector_id": normalized_id,
        "connector_status": record.get("status"),
        "detail": record.get("detail", ""),
        "latency_ms": record.get("latency_ms"),
        "last_checked_at": record.get("last_checked_at"),
    }


def execute_refresh_summary() -> dict[str, object]:
    reset_connector_probe_cache()
    reset_monitor_probe_cache()
    summary = build_watch_summary()
    return {
        "summary_status": summary.get("status"),
        "connectors_ok": summary.get("connectors", {}).get("ok"),
        "updated_at": summary.get("updated_at"),
    }


def execute_acknowledge_signal(record: dict[str, object]) -> dict[str, object]:
    payload = record.get("payload") if isinstance(record.get("payload"), dict) else {}
    signal_ids: list[str] = []
    raw_ids = payload.get("signal_ids")
    if isinstance(raw_ids, list):
        signal_ids = [str(item).strip() for item in raw_ids if str(item).strip()]

    target_id = str(record.get("target_id", "")).strip()
    if target_id:
        signal_ids.append(target_id)

    deduped = list(dict.fromkeys(signal_ids))
    if not deduped:
        raise WatchCommandError("target_id or payload.signal_ids is required for acknowledge_signal")

    acknowledged = acknowledge_signals(
        deduped,
        acknowledged_by=str(record.get("requested_by", "operator")),
    )
    return {
        "acknowledged": acknowledged,
        "count": len(acknowledged),
    }


def execute_watch_command(record: dict[str, object]) -> dict[str, object]:
    command_type = str(record.get("command_type", "")).strip()
    if command_type == "reprobe_connector":
        return execute_reprobe_connector(connector_id=str(record.get("target_id", "")))
    if command_type == "refresh_summary":
        return execute_refresh_summary()
    if command_type == "acknowledge_signal":
        return execute_acknowledge_signal(record)
    raise WatchCommandError(f"unsupported command_type: {command_type}")
