"""Shared HTTP POST helper for webhook-style delivery adapters."""

from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def post_json(url: str, payload: dict[str, Any], *, timeout_seconds: float = 5.0) -> None:
    body = json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", "User-Agent": "axon-watch-delivery/1.0"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            status = getattr(response, "status", 200)
            if status >= 400:
                raise HTTPError(url, status, f"HTTP {status}", hdrs=None, fp=None)
    except HTTPError as exc:
        raise HTTPError(
            url,
            exc.code,
            f"HTTP {exc.code}",
            hdrs=exc.headers,
            fp=exc.fp,
        ) from exc
    except URLError as exc:
        reason = str(getattr(exc, "reason", exc))
        if "timed out" in reason.lower():
            raise TimeoutError(reason) from exc
        raise ConnectionError(reason) from exc
