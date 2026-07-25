"""Persisted operator email settings (mailboxes, bridge, workspace hints)."""

from __future__ import annotations

import json
import os
import re
import uuid
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.persistence import run_store_sqlite

_SETTINGS_KEY = "default"
_SAFE_TOKEN_RE = re.compile(r"[^a-zA-Z0-9._@+-]+")

_DEFAULT_HINT_MAP: dict[str, str] = {
    "DashPro": "workspace_dashpro",
    "Axon": "workspace_axon_watch",
    "Axon Watch": "workspace_axon_watch",
    "Axon Local": "workspace_axon_local",
}


def _configured_db_path() -> str | None:
    return os.environ.get("AXON_WATCH_CONTROL_PLANE_DB")


def _connection():
    return run_store_sqlite.connect(_configured_db_path())


@contextmanager
def _managed_connection():
    connection = _connection()
    try:
        yield connection
    finally:
        connection.close()


def _utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def projection_path() -> Path:
    configured = os.environ.get("AXON_WATCH_EMAIL_SETTINGS_FILE", "").strip()
    if configured:
        path = Path(configured).expanduser()
        if not path.is_absolute():
            path = (_repo_root() / path).resolve()
        return path
    return (_repo_root() / "config" / "email-operator-settings.json").resolve()


def default_settings() -> dict[str, Any]:
    return {
        "bridge_enabled": False,
        "bridge_workspace_id": "7",
        "stub_enabled": True,
        "workspace_hint_map": dict(_DEFAULT_HINT_MAP),
        "accounts": [],
    }


def _safe_token(value: str) -> str:
    cleaned = _SAFE_TOKEN_RE.sub("_", value.strip())[:80].strip("_")
    return cleaned or "mailbox"


def vault_secret_name(*, workspace_id: str, email_address: str, kind: str) -> str:
    return f"email:{_safe_token(workspace_id)}:{_safe_token(email_address)}:{kind}"


def _normalize_imap(raw: dict[str, Any] | None, email_address: str) -> dict[str, Any]:
    payload = raw if isinstance(raw, dict) else {}
    port = int(payload.get("port") or 993)
    return {
        "host": str(payload.get("host") or "").strip(),
        "port": port,
        "username": str(payload.get("username") or email_address).strip() or email_address,
        "ssl": bool(payload.get("ssl", True)),
        "folder": str(payload.get("folder") or "INBOX").strip() or "INBOX",
        "password_ref": str(payload.get("password_ref") or "").strip(),
    }


def _normalize_smtp(raw: dict[str, Any] | None, email_address: str) -> dict[str, Any]:
    payload = raw if isinstance(raw, dict) else {}
    port = int(payload.get("port") or 465)
    ssl = bool(payload.get("ssl", port == 465))
    starttls = bool(payload.get("starttls", False)) if port != 465 else False
    if port == 465:
        ssl = True
        starttls = False
    return {
        "host": str(payload.get("host") or "").strip(),
        "port": port,
        "username": str(payload.get("username") or email_address).strip() or email_address,
        "ssl": ssl,
        "starttls": starttls,
        "from_email": str(payload.get("from_email") or email_address).strip() or email_address,
        "password_ref": str(payload.get("password_ref") or "").strip(),
    }


def _normalize_monitor(raw: dict[str, Any] | None) -> dict[str, Any]:
    payload = raw if isinstance(raw, dict) else {}
    poll = int(payload.get("poll_seconds") or 60)
    poll = max(15, min(poll, 3600))
    return {
        "enabled": bool(payload.get("enabled", True)),
        "poll_seconds": poll,
    }


def normalize_account(raw: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    email_address = str(raw.get("email_address") or raw.get("external_id") or "").strip()
    workspace_id = str(raw.get("workspace_id") or "").strip()
    if not email_address or not workspace_id:
        return None
    account_id = str(raw.get("account_id") or "").strip() or str(uuid.uuid4())
    return {
        "account_id": account_id,
        "workspace_id": workspace_id,
        "email_address": email_address,
        "display_name": str(raw.get("display_name") or email_address).strip() or email_address,
        "imap": _normalize_imap(
            raw.get("imap") if isinstance(raw.get("imap"), dict) else None, email_address
        ),
        "smtp": _normalize_smtp(
            raw.get("smtp") if isinstance(raw.get("smtp"), dict) else None, email_address
        ),
        "monitor": _normalize_monitor(
            raw.get("monitor") if isinstance(raw.get("monitor"), dict) else None
        ),
        "updated_at": str(raw.get("updated_at") or _utc_now_iso()),
    }


def normalize_settings(raw: dict[str, Any] | None) -> dict[str, Any]:
    defaults = default_settings()
    if not isinstance(raw, dict):
        return defaults
    hint_map = defaults["workspace_hint_map"]
    if isinstance(raw.get("workspace_hint_map"), dict):
        hint_map = {
            str(k).strip(): str(v).strip()
            for k, v in raw["workspace_hint_map"].items()
            if str(k).strip() and str(v).strip()
        } or hint_map
    accounts: list[dict[str, Any]] = []
    for entry in raw.get("accounts") or []:
        account = normalize_account(entry if isinstance(entry, dict) else None)
        if account is not None:
            accounts.append(account)
    return {
        "bridge_enabled": bool(raw.get("bridge_enabled", defaults["bridge_enabled"])),
        "bridge_workspace_id": str(
            raw.get("bridge_workspace_id") or defaults["bridge_workspace_id"]
        ).strip()
        or "7",
        "stub_enabled": bool(raw.get("stub_enabled", defaults["stub_enabled"])),
        "workspace_hint_map": hint_map,
        "accounts": accounts,
    }


def reset_store() -> None:
    with _managed_connection() as connection:
        connection.execute("DELETE FROM email_operator_settings")
        connection.commit()


def _read_projection_file() -> dict[str, Any] | None:
    path = projection_path()
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def load_settings() -> dict[str, Any]:
    with _managed_connection() as connection:
        row = connection.execute(
            "SELECT settings_json FROM email_operator_settings WHERE settings_key = ?",
            (_SETTINGS_KEY,),
        ).fetchone()
    if row is None:
        projection = _read_projection_file()
        if projection and (
            projection.get("accounts")
            or projection.get("bridge_enabled")
            or projection.get("stub_enabled") is False
        ):
            # Recover after DB wipe/path drift: projection is the durable operator mirror.
            return save_settings(normalize_settings(projection))["settings"]
        return default_settings()
    payload = json.loads(str(row["settings_json"]))
    if not isinstance(payload, dict):
        return default_settings()
    return normalize_settings(payload)


def write_projection(settings: dict[str, Any]) -> Path:
    path = projection_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    projection = {
        "schema_version": 1,
        "bridge_enabled": bool(settings.get("bridge_enabled")),
        "bridge_workspace_id": str(settings.get("bridge_workspace_id") or "7"),
        "stub_enabled": bool(settings.get("stub_enabled", True)),
        "workspace_hint_map": dict(settings.get("workspace_hint_map") or {}),
        "accounts": [
            {
                "account_id": account["account_id"],
                "workspace_id": account["workspace_id"],
                "email_address": account["email_address"],
                "display_name": account["display_name"],
                "imap": {
                    "host": account["imap"]["host"],
                    "port": account["imap"]["port"],
                    "username": account["imap"]["username"],
                    "ssl": account["imap"]["ssl"],
                    "folder": account["imap"]["folder"],
                    "password_ref": account["imap"]["password_ref"],
                },
                "smtp": {
                    "host": account["smtp"]["host"],
                    "port": account["smtp"]["port"],
                    "username": account["smtp"]["username"],
                    "ssl": account["smtp"]["ssl"],
                    "starttls": account["smtp"]["starttls"],
                    "from_email": account["smtp"]["from_email"],
                    "password_ref": account["smtp"]["password_ref"],
                },
                "monitor": account["monitor"],
                "updated_at": account["updated_at"],
            }
            for account in settings.get("accounts") or []
        ],
        "updated_at": _utc_now_iso(),
    }
    path.write_text(json.dumps(projection, indent=2) + "\n", encoding="utf-8")
    return path


def save_settings(settings: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_settings(settings)
    updated_at = _utc_now_iso()
    payload = json.dumps(normalized)
    with _managed_connection() as connection:
        connection.execute(
            """
            INSERT INTO email_operator_settings (settings_key, settings_json, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(settings_key) DO UPDATE SET
                settings_json = excluded.settings_json,
                updated_at = excluded.updated_at
            """,
            (_SETTINGS_KEY, payload, updated_at),
        )
        connection.commit()
    write_projection(normalized)
    return {"settings": deepcopy(normalized), "updated_at": updated_at}


def upsert_account(account_payload: dict[str, Any]) -> dict[str, Any]:
    settings = load_settings()
    account = normalize_account(account_payload)
    if account is None:
        raise ValueError("email_address and workspace_id are required")
    account["updated_at"] = _utc_now_iso()
    accounts = list(settings.get("accounts") or [])
    replaced = False
    for index, existing in enumerate(accounts):
        if existing.get("account_id") == account["account_id"] or (
            existing.get("workspace_id") == account["workspace_id"]
            and str(existing.get("email_address") or "").lower()
            == account["email_address"].lower()
        ):
            if not account["imap"]["password_ref"]:
                account["imap"]["password_ref"] = existing["imap"].get("password_ref") or ""
            if not account["smtp"]["password_ref"]:
                account["smtp"]["password_ref"] = existing["smtp"].get("password_ref") or ""
            account["account_id"] = existing["account_id"]
            accounts[index] = account
            replaced = True
            break
    if not replaced:
        accounts.append(account)
    settings["accounts"] = accounts
    result = save_settings(settings)
    result["account"] = account
    return result


def delete_account(account_id: str) -> dict[str, Any]:
    settings = load_settings()
    before = len(settings.get("accounts") or [])
    settings["accounts"] = [
        account
        for account in settings.get("accounts") or []
        if str(account.get("account_id")) != str(account_id)
    ]
    if len(settings["accounts"]) == before:
        raise KeyError(f"account not found: {account_id}")
    return save_settings(settings)
