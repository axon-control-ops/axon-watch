"""Resolve real IMAP folder names per account and list their messages.

Folder naming is provider-specific (cPanel mailboxes here use
"INBOX.Sent"/"INBOX.spam"/"INBOX.Archive"; other providers use different
paths and separators). Rather than guessing a name, this reads the IMAP
LIST response's RFC 6154 SPECIAL-USE attributes (\\Sent, \\Junk, \\Archive,
\\Trash, \\Drafts) that mail servers already attach to each folder, and maps
those to the roles the UI cares about.
"""

from __future__ import annotations

import imaplib
import re
import time
from typing import Any

from app.signals.email_imap_poll import _resolve_password, fetch_account_folder_messages

# A live folder fetch is a real, uncached IMAP round trip per message (no
# connection reuse, one shared-hosting mailbox measured at ~16s for 5
# messages) -- far too slow to re-run on every tab click. Folder structure
# essentially never changes mid-session; message lists are fine slightly
# stale for a UI that isn't the triage/action surface (that's Inbox, which
# already has its own poll+cache).
_FOLDER_LIST_TTL_SECONDS = 300.0
_FOLDER_MESSAGES_TTL_SECONDS = 60.0
_folder_list_cache: dict[str, tuple[float, dict[str, str]]] = {}
_folder_messages_cache: dict[str, tuple[float, list[dict[str, Any]]]] = {}

_ROLE_BY_FLAG = {
    "\\sent": "sent",
    "\\junk": "junk",
    "\\archive": "archive",
    "\\trash": "trash",
    "\\drafts": "drafts",
}

_LIST_LINE_RE = re.compile(
    r'^\((?P<flags>[^)]*)\)\s+"(?P<delim>[^"]*)"\s+(?P<name>.+)$'
)


def _parse_list_line(raw: bytes) -> tuple[list[str], str] | None:
    try:
        text = raw.decode("utf-8", errors="replace").strip()
    except Exception:  # noqa: BLE001
        return None
    match = _LIST_LINE_RE.match(text)
    if not match:
        return None
    flags = [flag.strip().lower() for flag in match.group("flags").split() if flag.strip()]
    name = match.group("name").strip()
    if name.startswith('"') and name.endswith('"'):
        name = name[1:-1]
    return flags, name


def list_account_folders(account: dict[str, Any]) -> dict[str, str]:
    """Return {role: real_folder_name} for one account -- always includes "inbox"."""
    account_id = str(account.get("account_id") or "").strip()
    now = time.monotonic()
    if account_id:
        cached = _folder_list_cache.get(account_id)
        if cached is not None and (now - cached[0]) < _FOLDER_LIST_TTL_SECONDS:
            return dict(cached[1])

    roles = _list_account_folders_uncached(account)
    if account_id and roles:
        _folder_list_cache[account_id] = (now, dict(roles))
    return roles


def _list_account_folders_uncached(account: dict[str, Any]) -> dict[str, str]:
    imap = account.get("imap") if isinstance(account.get("imap"), dict) else {}
    host = str(imap.get("host") or "").strip()
    port = int(imap.get("port") or 993)
    username = str(imap.get("username") or account.get("email_address") or "").strip()
    use_ssl = bool(imap.get("ssl", True))
    password = _resolve_password(str(imap.get("password_ref") or ""))
    if not (host and username and password):
        return {}

    roles: dict[str, str] = {}
    client: imaplib.IMAP4 | imaplib.IMAP4_SSL | None = None
    try:
        client = imaplib.IMAP4_SSL(host, port, timeout=12) if use_ssl else imaplib.IMAP4(host, port, timeout=12)
        status, _ = client.login(username, password)
        if status != "OK":
            return {}
        status, data = client.list()
        if status != "OK":
            return {}
        for raw in data or []:
            if not isinstance(raw, bytes):
                continue
            parsed = _parse_list_line(raw)
            if not parsed:
                continue
            flags, name = parsed
            if name.upper() == "INBOX":
                roles.setdefault("inbox", name)
                continue
            for flag in flags:
                role = _ROLE_BY_FLAG.get(flag)
                if role and role not in roles:
                    roles[role] = name
        return roles
    except Exception:  # noqa: BLE001 — folder discovery is best-effort
        return roles
    finally:
        if client is not None:
            try:
                client.logout()
            except Exception:  # noqa: BLE001
                pass


def fetch_role_messages(
    account: dict[str, Any],
    role: str,
    *,
    limit: int = 25,
) -> list[dict[str, Any]]:
    """Fetch messages from the folder matching `role` ("sent", "junk", ...)."""
    normalized_role = role.strip().lower()
    account_id = str(account.get("account_id") or "").strip()
    cache_key = f"{account_id}:{normalized_role}:{limit}"
    now = time.monotonic()
    if account_id:
        cached = _folder_messages_cache.get(cache_key)
        if cached is not None and (now - cached[0]) < _FOLDER_MESSAGES_TTL_SECONDS:
            return list(cached[1])

    if normalized_role == "inbox":
        imap = account.get("imap") if isinstance(account.get("imap"), dict) else {}
        folder = str(imap.get("folder") or "INBOX").strip() or "INBOX"
        messages = fetch_account_folder_messages(
            account, folder, limit=limit, require_monitor_enabled=False
        )
    else:
        folders = list_account_folders(account)
        folder = folders.get(normalized_role)
        messages = (
            fetch_account_folder_messages(
                account, folder, limit=limit, require_monitor_enabled=False
            )
            if folder
            else []
        )

    if account_id and messages:
        _folder_messages_cache[cache_key] = (now, list(messages))
    return messages
