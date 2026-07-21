"""HTTP helpers for control-plane → watch service calls (Gate 2 internal token)."""

from __future__ import annotations

import os


def watch_base_url() -> str:
    return os.environ.get(
        "AXON_WATCH_WATCH_SERVICE_BASE_URL",
        "http://127.0.0.1:8788",
    ).rstrip("/")


def watch_request_headers(*, content_type: str | None = None) -> dict[str, str]:
    headers = {"Accept": "application/json"}
    if content_type:
        headers["Content-Type"] = content_type
    token = os.environ.get("AXON_WATCH_INTERNAL_SERVICE_TOKEN", "").strip()
    if token:
        headers["X-Axon-Internal-Token"] = token
    return headers
