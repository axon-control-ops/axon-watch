"""Bounded HTTP health probes for third-party and public endpoints."""

from __future__ import annotations

import json
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.monitors.github_probe_headers import is_github_api_url, looks_like_github_rate_limit


def _github_forbidden_detail(*, status_code: int, target: str, body: str = "", headers: object = None) -> str | None:
    """Explain GitHub API 401/403/429 as config/quota, not a platform outage."""
    code = int(status_code)
    if not is_github_api_url(target) or code not in {401, 403, 429}:
        return None
    if code == 401:
        return (
            f"GitHub API HTTP 401 from {target} — "
            "invalid or placeholder probe token, not a GitHub outage"
        )
    if looks_like_github_rate_limit(status_code=code, body=body, headers=headers):
        return (
            f"GitHub API rate limit for this host (HTTP {code}) — "
            "not an outage; use an authenticated probe token or wait for reset"
        )
    return (
        f"GitHub API HTTP {code} from {target} — "
        "usually a missing probe token or rate limit, not a GitHub outage"
    )


def _exception_text(exc: BaseException) -> str:
    parts = [str(exc)]
    if isinstance(exc, URLError) and getattr(exc, "reason", None) is not None:
        parts.append(str(exc.reason))
    return " ".join(parts).lower()


def _is_transient_dns_failure(exc: BaseException) -> bool:
    """True for resolver blips (EAI_AGAIN / Errno -3), not permanent NXDOMAIN."""
    text = _exception_text(exc)
    return (
        "temporary failure in name resolution" in text
        or "errno -3" in text
        or "eai_again" in text
    )


def check_http_health(
    *,
    url: str,
    timeout_seconds: float = 5.0,
    expect_status: int = 200,
    expect_json_status: str | None = None,
    headers: dict[str, str] | None = None,
    retries: int = 2,
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

    attempts = max(1, int(retries) + 1)
    response_headers = None
    body = ""
    status_code = 0
    last_dns_exc: BaseException | None = None

    for attempt in range(attempts):
        try:
            request = Request(target, headers=request_headers, method="GET")
            with urlopen(request, timeout=max(0.5, float(timeout_seconds))) as response:
                status_code = int(response.status)
                response_headers = response.headers
                body = response.read(8192).decode("utf-8", errors="replace")
            break
        except HTTPError as exc:
            status_code = int(exc.code)
            response_headers = exc.headers
            body = exc.read(8192).decode("utf-8", errors="replace") if exc.fp else ""
            github_detail = _github_forbidden_detail(
                status_code=status_code,
                target=target,
                body=body,
                headers=response_headers,
            )
            if github_detail:
                return "warning", github_detail
            if status_code >= 500:
                return "critical", f"HTTP {status_code} from {target}"
            return "warning", f"HTTP {status_code} from {target}"
        except (TimeoutError, URLError, OSError, ValueError) as exc:
            if _is_transient_dns_failure(exc):
                last_dns_exc = exc
                if attempt + 1 < attempts:
                    time.sleep(min(5.0, 1.5 * (attempt + 1)))
                    continue
                return (
                    "warning",
                    (
                        f"HTTP health probe DNS temporarily failed for {target}: {exc} — "
                        "local name resolution blip, not a confirmed upstream outage"
                    ),
                )
            return "critical", f"HTTP health probe failed: {exc}"
    else:
        # Exhausted DNS retries without break (defensive; loop returns above).
        if last_dns_exc is not None:
            return (
                "warning",
                (
                    f"HTTP health probe DNS temporarily failed for {target}: {last_dns_exc} — "
                    "local name resolution blip, not a confirmed upstream outage"
                ),
            )
        return "critical", f"HTTP health probe failed for {target}"

    expected = int(expect_status)
    if status_code != expected:
        github_detail = _github_forbidden_detail(
            status_code=status_code,
            target=target,
            body=body,
            headers=response_headers,
        )
        if github_detail:
            return "warning", github_detail
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
