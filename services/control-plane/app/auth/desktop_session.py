"""Desktop session cookie auth for packaged Tauri same-origin UI."""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time
from typing import Any

SESSION_COOKIE = "axon_desktop_session"
SESSION_HEADER = "x-axon-desktop-session"
_BOOTSTRAP_TTL_SECONDS = 120

# One-time bootstrap codes minted by the desktop shell (token -> expires_at).
_pending_bootstrap: dict[str, float] = {}


def _session_secret() -> bytes:
    raw = (
        os.environ.get("AXON_WATCH_DESKTOP_SESSION_SECRET")
        or os.environ.get("AXON_WATCH_OPERATOR_TOKEN")
        or "axon-desktop-dev"
    ).strip()
    return hashlib.sha256(raw.encode("utf-8")).digest()


def mint_bootstrap_code() -> str:
    code = secrets.token_urlsafe(24)
    _pending_bootstrap[code] = time.time() + _BOOTSTRAP_TTL_SECONDS
    return code


def consume_bootstrap_code(code: str) -> bool:
    expires = _pending_bootstrap.pop(code.strip(), None)
    if expires is None:
        return False
    return time.time() <= expires


def issue_session_token() -> str:
    nonce = secrets.token_urlsafe(18)
    digest = hmac.new(_session_secret(), nonce.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{nonce}.{digest}"


def validate_session_token(token: str | None) -> bool:
    if not token or "." not in token:
        return False
    nonce, digest = token.rsplit(".", 1)
    expected = hmac.new(_session_secret(), nonce.encode("utf-8"), hashlib.sha256).hexdigest()
    return secrets.compare_digest(digest, expected)


def extract_session_token(cookies: Any, headers: Any) -> str:
    header_token = ""
    if headers is not None:
        header_token = (headers.get(SESSION_HEADER) or "").strip()
    if header_token:
        return header_token
    if cookies is None:
        return ""
    try:
        return str(cookies.get(SESSION_COOKIE) or "").strip()
    except Exception:
        return ""


def clear_pending_bootstrap() -> None:
    _pending_bootstrap.clear()
