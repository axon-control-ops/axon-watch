"""Bounded HTTP health probes for third-party and public endpoints."""

from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def check_http_health(
    *,
    url: str,
    timeout_seconds: float = 5.0,
    expect_status: int = 200,
    expect_json_status: str | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[str, str]:
    """Probe one URL and return (status, detail).

    status is one of: ok | warning | critical | skipped
    """
    target = str(url or "").strip()
    if not target:
        return "skipped", "HTTP health check skipped: url missing"
    if "${" in target or target.startswith("$"):
        return "skipped", f"HTTP health check skipped: unresolved url placeholder ({target})"
    if "://" not in target:
        return "skipped", f"HTTP health check skipped: invalid url ({target})"

    request_headers = {"Accept": "*/*", "User-Agent": "Axon-Watch-Monitor/1.0"}
    if headers:
        request_headers.update({str(k): str(v) for k, v in headers.items() if str(k).strip()})

    try:
        request = Request(target, headers=request_headers, method="GET")
        with urlopen(request, timeout=max(0.5, float(timeout_seconds))) as response:
            status_code = int(response.status)
            body = response.read(8192).decode("utf-8", errors="replace")
    except HTTPError as exc:
        status_code = int(exc.code)
        body = exc.read(8192).decode("utf-8", errors="replace") if exc.fp else ""
        if status_code >= 500:
            return "critical", f"HTTP {status_code} from {target}"
        return "warning", f"HTTP {status_code} from {target}"
    except (TimeoutError, URLError, OSError, ValueError) as exc:
        return "critical", f"HTTP health probe failed: {exc}"

    expected = int(expect_status)
    if status_code != expected:
        severity = "critical" if status_code >= 500 else "warning"
        return severity, f"HTTP {status_code} (expected {expected}) from {target}"

    wanted = str(expect_json_status or "").strip()
    if wanted:
        try:
            payload: Any = json.loads(body) if body.strip() else None
        except json.JSONDecodeError:
            return "warning", f"reachable but non-JSON body from {target}"
        if not isinstance(payload, dict):
            return "warning", f"reachable but JSON was not an object from {target}"
        actual = str(payload.get("status") or "").strip()
        if actual and actual.lower() not in {wanted.lower(), "ok", "ready"}:
            return "warning", f"status={actual} from {target}"
        if actual and actual.lower() != wanted.lower() and wanted.lower() not in {"ok", "ready"}:
            return "warning", f"status={actual} (expected {wanted}) from {target}"

    return "ok", f"reachable ({status_code})"
