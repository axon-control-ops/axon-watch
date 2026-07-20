"""Gate 2 auth settings — local operator token + remote reachability."""

from __future__ import annotations

import os
from urllib.parse import urlparse

from app.config import _public_base_url


def auth_mode() -> str:
    raw = os.environ.get("AXON_WATCH_AUTH_MODE", "placeholder").strip().lower()
    if raw in {"", "placeholder", "off", "disabled", "none"}:
        return "off"
    if raw in {"local_token", "token", "required"}:
        return "local_token"
    return raw


def operator_token() -> str:
    return os.environ.get("AXON_WATCH_OPERATOR_TOKEN", "").strip()


def allow_loopback_bypass() -> bool:
    raw = os.environ.get("AXON_WATCH_AUTH_ALLOW_LOOPBACK", "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _host_is_loopback(host: str | None) -> bool:
    cleaned = str(host or "").strip().lower().split("%", 1)[0]
    if cleaned.startswith("[") and cleaned.endswith("]"):
        cleaned = cleaned[1:-1]
    return cleaned in {"127.0.0.1", "localhost", "::1", "0:0:0:0:0:0:0:1"}


def is_remotely_reachable() -> bool:
    """True when the operator surface is configured for non-loopback reachability."""
    forced = os.environ.get("AXON_WATCH_REMOTELY_REACHABLE", "").strip().lower()
    if forced in {"1", "true", "yes", "on"}:
        return True
    if forced in {"0", "false", "no", "off"}:
        return False
    public = _public_base_url()
    host = urlparse(public).hostname
    return not _host_is_loopback(host)


def client_is_loopback(host: str | None) -> bool:
    return _host_is_loopback(host)
