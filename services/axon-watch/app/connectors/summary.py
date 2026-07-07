"""Aggregate connector probe results for watch summary surfaces."""

from __future__ import annotations

from app.connectors.catalog import load_watch_connector_definitions
from app.connectors.probe import probe_connector
from app.signals.iso_time import utc_now_iso
from app.tunnel.slice_registry import load_tunnel_slice
from app.tunnel.tunnel_probe import probe_cloudflare_tunnel


def probe_all_connectors() -> list[dict[str, object]]:
    definitions = load_watch_connector_definitions()
    records = [probe_connector(definition) for definition in definitions.values()]
    tunnel_config = load_tunnel_slice()
    if tunnel_config is not None:
        records.append(probe_cloudflare_tunnel(tunnel_config))
    return records


def build_connectors_snapshot(items: list[dict[str, object]] | None = None) -> dict[str, object]:
    records = items if items is not None else probe_all_connectors()
    ok_count = sum(1 for item in records if item.get("status") == "ok")
    degraded_count = sum(1 for item in records if item.get("status") == "degraded")
    unavailable_count = sum(1 for item in records if item.get("status") == "unavailable")
    required_unavailable = sum(
        1
        for item in records
        if item.get("required") and item.get("status") != "ok"
    )

    return {
        "configured": len(records),
        "ok": ok_count,
        "degraded": degraded_count,
        "unavailable": unavailable_count,
        "required_unavailable": required_unavailable,
        "items": records,
        "updated_at": utc_now_iso(),
    }
