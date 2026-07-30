"""Gate 2 auth settings — local operator token + remote reachability."""

from __future__ import annotations

import os
from urllib.parse import urlparse

from app.config import _public_base_url


def configured_auth_mode() -> str:
    """Raw configured mode before remote-force rules."""
    raw = os.environ.get("AXON_WATCH_AUTH_MODE", "placeholder").strip().lower()
    if raw in {"", "placeholder", "off", "disabled", "none"}:
        return "off"
    if raw in {"local_token", "token", "required"}:
        return "local_token"
    return raw


def auth_mode() -> str:
    """
    Effective auth mode.

    Remotely reachable deployments always enforce ``local_token`` even when the
    env still says placeholder/off (Gate 2 residual: forced token mode on remote).
    """
    mode = configured_auth_mode()
    if mode == "off" and is_remotely_reachable():
        return "local_token"
    return mode


def operator_token() -> str:
    return os.environ.get("AXON_WATCH_OPERATOR_TOKEN", "").strip()


def allow_loopback_bypass() -> bool:
    # Remote surfaces must not accept anonymous loopback clients.
    if is_remotely_reachable():
        return False
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


def vault_auto_unlock_allowed() -> bool:
    """
    Whether control-plane may enable / rely on vault auto-unlock.

    Remotely reachable hosts refuse by default. Trusted always-on operator hosts
    may set AXON_WATCH_ALLOW_VAULT_AUTO_UNLOCK=1 without weakening local_token /
    origin / internal-service-token containment.
    """
    raw = os.environ.get("AXON_WATCH_ALLOW_VAULT_AUTO_UNLOCK", "").strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    return not is_remotely_reachable()


def client_is_loopback(host: str | None) -> bool:
    return _host_is_loopback(host)
