"""HTTP helpers for control-plane → watch service calls (token + optional mTLS)."""

from __future__ import annotations

import os
import ssl
from typing import Any
from urllib.request import Request, urlopen


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


def watch_ssl_context() -> ssl.SSLContext | None:
    """
    Optional client-certificate context for HTTPS watch calls.

    Set:
      AXON_WATCH_MTLS_CLIENT_CERT / AXON_WATCH_MTLS_CLIENT_KEY
      AXON_WATCH_MTLS_CA_FILE (recommended)
    """
    cert = os.environ.get("AXON_WATCH_MTLS_CLIENT_CERT", "").strip()
    key = os.environ.get("AXON_WATCH_MTLS_CLIENT_KEY", "").strip()
    if not cert or not key:
        return None
    ca = os.environ.get("AXON_WATCH_MTLS_CA_FILE", "").strip()
    if ca:
        context = ssl.create_default_context(cafile=ca)
    else:
        context = ssl.create_default_context()
    context.load_cert_chain(certfile=cert, keyfile=key)
    return context


def watch_urlopen(request: Request, *, timeout: float) -> Any:
    context = watch_ssl_context()
    if context is not None:
        return urlopen(request, timeout=timeout, context=context)
    return urlopen(request, timeout=timeout)
