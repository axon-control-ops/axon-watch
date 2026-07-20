"""HTTP health probes for configured watch connectors."""

from __future__ import annotations

import json
import time
from urllib.error import URLError
from urllib.request import Request, urlopen

from app.connectors.catalog import WatchConnectorDefinition
from app.probe_failure_detail import format_probe_failure
from app.signals.iso_time import utc_now_iso

ConnectorStatus = str  # ok | degraded | unavailable


def probe_connector(
    definition: WatchConnectorDefinition,
    *,
    timeout_seconds: float = 0.75,
) -> dict[str, object]:
    started = time.monotonic()
    checked_at = utc_now_iso()
    record: dict[str, object] = {
        "connector_id": definition.connector_id,
        "display_name": definition.display_name,
        "health_url": definition.health_url,
        "required": definition.required,
        "workspace_id": definition.workspace_id,
        "last_checked_at": checked_at,
    }

    try:
        request = Request(definition.health_url, headers={"Accept": "*/*"})
        with urlopen(request, timeout=timeout_seconds) as response:
            body = response.read(4096).decode("utf-8", errors="replace")
            latency_ms = int((time.monotonic() - started) * 1000)
            record["latency_ms"] = latency_ms

            if response.status != 200:
                record["status"] = "degraded"
                record["detail"] = f"HTTP {response.status}"
                return record

            detail = "reachable"
            if body.strip():
                try:
                    payload = json.loads(body)
                except json.JSONDecodeError:
                    payload = None
                if isinstance(payload, dict):
                    service_status = str(payload.get("status", "")).strip()
                    if service_status and service_status not in {"ok", "ready"}:
                        record["status"] = "degraded"
                        record["detail"] = f"status={service_status}"
                        return record
                    detail = service_status or detail

            record["status"] = "ok"
            record["detail"] = detail
            return record
    except (URLError, TimeoutError, OSError, ValueError) as exc:
        latency_ms = int((time.monotonic() - started) * 1000)
        record["latency_ms"] = latency_ms
        record["status"] = "unavailable"
        record["detail"] = format_probe_failure(exc, definition.health_url)
        return record
