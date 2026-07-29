"""HTTP health probes for configured watch connectors."""

from __future__ import annotations

import json
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.connectors.catalog import WatchConnectorDefinition
from app.monitors.github_probe_headers import (
    github_api_headers,
    is_github_api_url,
    looks_like_github_rate_limit,
)
from app.probe_failure_detail import format_probe_failure
from app.signals.iso_time import utc_now_iso
from app.vault.credential_resolver import merge_monitor_env

ConnectorStatus = str  # ok | degraded | unavailable

# Cloudflare often blocks the default Python-urllib User-Agent with 403.
# Keep aligned with services/axon-watch/app/tunnel/tunnel_probe.py.
_PROBE_HEADERS = {
    "Accept": "application/json, */*",
    "User-Agent": "Axon-X-ConnectorProbe/1.0 (+https://axon.edudashpro.org.za)",
}


def _connector_probe_headers(health_url: str) -> dict[str, str]:
    if is_github_api_url(health_url):
        headers = github_api_headers(merge_monitor_env())
        headers["User-Agent"] = _PROBE_HEADERS["User-Agent"]
        return headers
    return dict(_PROBE_HEADERS)


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
        request = Request(definition.health_url, headers=_connector_probe_headers(definition.health_url))
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
    except HTTPError as exc:
        latency_ms = int((time.monotonic() - started) * 1000)
        record["latency_ms"] = latency_ms
        # Non-200 HTTP responses raise HTTPError before status can be read.
        body = ""
        try:
            body = exc.read(4096).decode("utf-8", errors="replace") if exc.fp else ""
        except Exception:
            body = ""
        if looks_like_github_rate_limit(status_code=int(exc.code), body=body, headers=exc.headers):
            record["status"] = "degraded"
            record["detail"] = (
                f"HTTP {exc.code} rate limit (not an outage; authenticate GitHub probes)"
            )
            return record
        if is_github_api_url(definition.health_url) and int(exc.code) in {403, 429}:
            record["status"] = "degraded"
            record["detail"] = (
                f"HTTP {exc.code} GitHub auth/quota gap (not an outage; authenticate probes)"
            )
            return record
        record["status"] = "degraded"
        record["detail"] = f"HTTP {exc.code}"
        return record
    except (URLError, TimeoutError, OSError, ValueError) as exc:
        latency_ms = int((time.monotonic() - started) * 1000)
        record["latency_ms"] = latency_ms
        record["status"] = "unavailable"
        record["detail"] = format_probe_failure(exc, definition.health_url)
        return record
