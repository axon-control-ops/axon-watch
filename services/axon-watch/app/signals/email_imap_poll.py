"""Native IMAP poll for Axon-X configured mailboxes.

Reads operator email projection + unlocked vault passwords, fetches recent
messages, and returns watch-inbox-compatible message dicts.
"""

from __future__ import annotations

import email.header
import email.utils
import imaplib
import json
import os
import time
from datetime import UTC
from email import policy
from email.parser import BytesParser
from pathlib import Path
from typing import Any

from app.vault.operations import vault_resolve_named_secret
from app.vault.session import VaultSession

_CACHE_TTL_SECONDS = 45.0
_DEFAULT_LIMIT = 12
_cache_at = 0.0
_cache_payload: list[dict[str, Any]] | None = None


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _projection_path() -> Path:
    configured = os.environ.get("AXON_WATCH_EMAIL_SETTINGS_FILE", "").strip()
    if configured:
        path = Path(configured).expanduser()
        if not path.is_absolute():
            path = (_repo_root() / path).resolve()
        return path
    return (_repo_root() / "config" / "email-operator-settings.json").resolve()


def load_operator_email_projection() -> dict[str, Any]:
    path = _projection_path()
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _resolve_password(password_ref: str) -> str:
    ref = str(password_ref or "").strip()
    if not ref:
        return ""
    if not VaultSession.is_unlocked():
        return ""
    name = ref[6:] if ref.startswith("vault:") else ref
    return str(vault_resolve_named_secret(name) or "").strip()


def _decode_header(value: str) -> str:
    chunks: list[str] = []
    for part, charset in email.header.decode_header(value or ""):
        if isinstance(part, bytes):
            chunks.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            chunks.append(str(part or ""))
    return " ".join(chunks).strip()


def _plain_text(msg: email.message.Message) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and not part.get_filename():
                try:
                    return str(part.get_content())
                except Exception:  # noqa: BLE001
                    payload = part.get_payload(decode=True) or b""
                    charset = part.get_content_charset() or "utf-8"
                    return payload.decode(charset, errors="replace")
        return ""
    try:
        return str(msg.get_content())
    except Exception:  # noqa: BLE001
        payload = msg.get_payload(decode=True) or b""
        charset = msg.get_content_charset() or "utf-8"
        return payload.decode(charset, errors="replace") if isinstance(payload, bytes) else str(payload)


def _message_summary(raw_message: bytes, *, uid: str, account_email: str) -> dict[str, Any]:
    msg = BytesParser(policy=policy.default).parsebytes(raw_message)
    body_text = _plain_text(msg)
    snippet = " ".join(body_text.split())[:240]
    sent_at = ""
    try:
        parsed = email.utils.parsedate_to_datetime(str(msg.get("Date") or "").strip())
        if parsed is not None:
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            sent_at = parsed.astimezone(UTC).isoformat().replace("+00:00", "Z")
    except Exception:  # noqa: BLE001
        sent_at = ""
    return {
        "uid": str(uid or "").strip(),
        "message_id": str(msg.get("Message-ID") or "").strip() or f"{account_email}:{uid}",
        "subject": _decode_header(str(msg.get("Subject") or "").strip()),
        "from": _decode_header(str(msg.get("From") or "").strip()),
        "text": body_text,
        "snippet": snippet,
        "sent_at": sent_at,
        "account_email": account_email,
    }


def _fetch_account_messages(account: dict[str, Any], *, limit: int) -> list[dict[str, Any]]:
    monitor = account.get("monitor") if isinstance(account.get("monitor"), dict) else {}
    if not bool(monitor.get("enabled", True)):
        return []
    imap = account.get("imap") if isinstance(account.get("imap"), dict) else {}
    host = str(imap.get("host") or "").strip()
    port = int(imap.get("port") or 993)
    username = str(imap.get("username") or account.get("email_address") or "").strip()
    folder = str(imap.get("folder") or "INBOX").strip() or "INBOX"
    use_ssl = bool(imap.get("ssl", True))
    password = _resolve_password(str(imap.get("password_ref") or ""))
    account_email = str(account.get("email_address") or username).strip()
    if not (host and username and password):
        return []

    client: imaplib.IMAP4 | imaplib.IMAP4_SSL | None = None
    try:
        client = imaplib.IMAP4_SSL(host, port, timeout=12) if use_ssl else imaplib.IMAP4(host, port, timeout=12)
        status, _ = client.login(username, password)
        if status != "OK":
            return []
        select_status, _ = client.select(folder, readonly=True)
        if select_status != "OK":
            return []
        search_status, data = client.uid("search", None, "ALL")
        if search_status != "OK":
            return []
        uids = [item for item in (data[0] or b"").decode().split() if item.strip()]
        selected = uids[-max(1, limit) :]
        messages: list[dict[str, Any]] = []
        for uid in selected:
            fetch_status, fetch_parts = client.uid("fetch", uid, "(RFC822)")
            if fetch_status != "OK":
                continue
            raw_bytes = b""
            for part in fetch_parts or []:
                if isinstance(part, tuple) and len(part) >= 2:
                    raw_bytes = bytes(part[1] or b"")
                    break
            if not raw_bytes:
                continue
            messages.append(_message_summary(raw_bytes, uid=uid, account_email=account_email))
        return messages
    except Exception:  # noqa: BLE001 — poll failures fall through to bridge/stub
        return []
    finally:
        if client is not None:
            try:
                client.logout()
            except Exception:  # noqa: BLE001
                pass


def fetch_native_email_messages(
    *,
    limit_per_account: int = _DEFAULT_LIMIT,
    force: bool = False,
) -> list[dict[str, Any]] | None:
    """Return recent mailbox messages, or None when native poll is unavailable."""

    global _cache_at, _cache_payload
    projection = load_operator_email_projection()
    accounts = [
        account
        for account in (projection.get("accounts") or [])
        if isinstance(account, dict)
    ]
    if not accounts:
        return None
    if not VaultSession.is_unlocked():
        return None

    ready = 0
    for account in accounts:
        imap = account.get("imap") if isinstance(account.get("imap"), dict) else {}
        if _resolve_password(str(imap.get("password_ref") or "")):
            ready += 1
    if ready == 0:
        return None

    now = time.monotonic()
    if (
        not force
        and _cache_payload is not None
        and (now - _cache_at) < _CACHE_TTL_SECONDS
    ):
        return list(_cache_payload)

    messages: list[dict[str, Any]] = []
    for account in accounts:
        messages.extend(_fetch_account_messages(account, limit=limit_per_account))
    messages.sort(key=lambda item: str(item.get("sent_at") or ""), reverse=True)
    _cache_at = now
    _cache_payload = list(messages)
    return messages
