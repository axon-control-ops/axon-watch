"""Vault core operations: setup, unlock, CRUD, provider resolution."""

from __future__ import annotations

import base64
import hmac
import os
from typing import Any, Optional

from app.vault.crypto import (
    decrypt,
    derive_key,
    encrypt,
    generate_qr_data_uri,
    generate_totp_secret,
    hash_password_for_storage,
    verify_totp,
)
from app.vault.import_store import load_vault_import
from app.vault.provider_aliases import (
    PROVIDER_VAULT_NAMES,
    PROVIDER_VAULT_URLS,
)
from app.vault.session import (
    VaultSession,
    auto_unlock_enabled,
    load_auto_unlock_keyfile,
    remove_auto_unlock_keyfile,
    save_auto_unlock_keyfile,
)
from app.vault.store import get_setting, set_setting, vault_connection


def vault_is_setup() -> bool:
    with vault_connection() as conn:
        salt = get_setting(conn, "vault_salt")
        return bool(salt)


def setup_vault(master_password: str) -> dict[str, str]:
    salt = os.urandom(32)
    salt_b64 = base64.b64encode(salt).decode("ascii")
    pw_hash = hash_password_for_storage(master_password, salt)
    totp_secret = generate_totp_secret()
    key = derive_key(master_password, salt)
    encrypted_totp = encrypt(totp_secret, key)

    with vault_connection() as conn:
        set_setting(conn, "vault_salt", salt_b64)
        set_setting(conn, "vault_pw_hash", pw_hash)
        set_setting(conn, "vault_totp_enc", encrypted_totp)

    return {"totp_secret": totp_secret, "qr_data_uri": generate_qr_data_uri(totp_secret)}


def unlock_vault(
    master_password: str,
    totp_code: str,
    *,
    session_ttl: int = VaultSession.DEFAULT_TTL,
) -> tuple[bool, str]:
    with vault_connection() as conn:
        salt_b64 = get_setting(conn, "vault_salt")
        if not salt_b64:
            return False, "Vault not set up"
        salt = base64.b64decode(salt_b64)
        key = derive_key(master_password, salt)
        pw_hash = hash_password_for_storage(master_password, salt)
        stored_hash = get_setting(conn, "vault_pw_hash")
        if not hmac.compare_digest(pw_hash, stored_hash):
            return False, "Incorrect master password"
        enc_totp = get_setting(conn, "vault_totp_enc")
        try:
            totp_secret = decrypt(enc_totp, key)
        except Exception:
            return False, "Vault data corrupted"
        if not verify_totp(totp_secret, totp_code.strip()):
            return False, "Invalid 2FA code"

    VaultSession.unlock(key, session_ttl=session_ttl)
    migrate_legacy_import_file()
    return True, ""


def lock_vault() -> None:
    VaultSession.lock()


def vault_status_core() -> dict[str, object]:
    return {
        "is_setup": vault_is_setup(),
        "is_unlocked": VaultSession.is_unlocked(),
        "ttl_remaining": VaultSession.ttl_remaining(),
        "auto_unlock_enabled": auto_unlock_enabled(),
    }


def vault_list_secrets() -> list[dict[str, Any]]:
    with vault_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, name, category, username, url, notes_preview, created_at, updated_at
            FROM vault_secrets ORDER BY category, name
            """
        ).fetchall()
        return [dict(row) for row in rows]


def vault_get_secret(secret_id: int, key: bytes) -> Optional[dict[str, Any]]:
    with vault_connection() as conn:
        row = conn.execute("SELECT * FROM vault_secrets WHERE id = ?", (secret_id,)).fetchone()
        if not row:
            return None
        record = dict(row)
    try:
        record["password"] = decrypt(record["password_enc"], key) if record.get("password_enc") else ""
        record["notes"] = decrypt(record["notes_enc"], key) if record.get("notes_enc") else ""
    except Exception:
        return None
    record.pop("password_enc", None)
    record.pop("notes_enc", None)
    return record


def vault_add_secret(
    key: bytes,
    name: str,
    category: str,
    username: str,
    password: str,
    url: str,
    notes: str,
) -> int:
    password_enc = encrypt(password, key) if password else ""
    notes_enc = encrypt(notes, key) if notes else ""
    notes_preview = notes[:30] + "..." if len(notes) > 30 else notes
    with vault_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO vault_secrets
                (name, category, username, password_enc, url, notes_enc, notes_preview)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (name, category, username, password_enc, url, notes_enc, notes_preview),
        )
        return int(cur.lastrowid)


def vault_update_secret(
    key: bytes,
    secret_id: int,
    name: str,
    category: str,
    username: str,
    password: str,
    url: str,
    notes: str,
) -> None:
    password_enc = encrypt(password, key) if password else ""
    notes_enc = encrypt(notes, key) if notes else ""
    notes_preview = notes[:30] + "..." if len(notes) > 30 else notes
    with vault_connection() as conn:
        conn.execute(
            """
            UPDATE vault_secrets SET
                name=?, category=?, username=?, password_enc=?,
                url=?, notes_enc=?, notes_preview=?, updated_at=datetime('now')
            WHERE id=?
            """,
            (name, category, username, password_enc, url, notes_enc, notes_preview, secret_id),
        )


def vault_delete_secret(secret_id: int) -> None:
    with vault_connection() as conn:
        conn.execute("DELETE FROM vault_secrets WHERE id = ?", (secret_id,))


def vault_find_by_name(name: str) -> Optional[dict[str, Any]]:
    with vault_connection() as conn:
        row = conn.execute(
            "SELECT id, name FROM vault_secrets WHERE lower(trim(name)) = lower(trim(?)) LIMIT 1",
            (name,),
        ).fetchone()
        return dict(row) if row else None


def vault_resolve_named_secret(secret_name: str) -> str:
    key = VaultSession.get_key()
    if key is None:
        return ""
    name = str(secret_name or "").strip()
    if not name:
        return ""
    row = vault_find_by_name(name)
    if not row:
        return ""
    secret = vault_get_secret(int(row["id"]), key)
    if secret and secret.get("password"):
        return str(secret["password"]).strip()
    return ""


def vault_named_secrets_map(names: tuple[str, ...]) -> dict[str, str]:
    resolved: dict[str, str] = {}
    for name in names:
        value = vault_resolve_named_secret(name)
        if value:
            resolved[name] = value
    return resolved


def _canonical_secret_label(value: str) -> str:
    raw = str(value or "").strip().lower()
    if not raw:
        return ""
    parts: list[str] = []
    token: list[str] = []
    for ch in raw:
        if ch.isalnum():
            token.append(ch)
        else:
            if token:
                parts.append("".join(token))
                token = []
    if token:
        parts.append("".join(token))
    return " ".join(parts)


def _provider_secret_match_score(
    provider_id: str,
    secret_name: str,
    secret_url: str,
    candidate_names: list[str],
    url_patterns: list[str],
) -> int:
    name_raw = str(secret_name or "").strip().lower()
    url_raw = str(secret_url or "").strip().lower()
    name = _canonical_secret_label(name_raw)
    best = 0
    for candidate in candidate_names:
        cand_raw = str(candidate or "").strip().lower()
        if not cand_raw:
            continue
        cand = _canonical_secret_label(cand_raw)
        if not cand:
            continue
        if name == cand or name_raw == cand_raw:
            best = max(best, 500)
            continue
        if name.startswith(f"{cand} ") or name.endswith(f" {cand}") or f" {cand} " in f" {name} ":
            best = max(best, 420)
            continue
        if cand in name:
            best = max(best, 300)
    for domain in url_patterns:
        dom = str(domain or "").strip().lower()
        if dom and dom in url_raw:
            best = max(best, 200)
    if provider_id == "nvidia_nim" and "cursor" in name:
        best = min(best, 50)
    return best


def vault_resolve_provider_key(provider_id: str) -> str:
    key = VaultSession.get_key()
    if key is None:
        return ""
    names = PROVIDER_VAULT_NAMES.get(provider_id, [provider_id])
    url_patterns = PROVIDER_VAULT_URLS.get(provider_id, [])
    metadata = vault_list_secrets()
    candidates: list[tuple[int, str, int]] = []
    for row in metadata:
        score = _provider_secret_match_score(
            provider_id,
            str(row["name"] or ""),
            str(row["url"] or ""),
            names,
            url_patterns,
        )
        if score <= 0:
            continue
        recency = str(row["updated_at"] or row["created_at"] or "")
        candidates.append((score, recency, int(row["id"])))
    for _score, _recency, secret_id in sorted(candidates, key=lambda item: (item[0], item[1], item[2]), reverse=True):
        secret = vault_get_secret(secret_id, key)
        if secret and secret.get("password"):
            return str(secret["password"])
    return ""


def vault_resolve_all_provider_keys() -> dict[str, str]:
    key = VaultSession.get_key()
    if key is None:
        return {}
    metadata = vault_list_secrets()
    resolved: dict[str, str] = {}
    for provider_id, names in PROVIDER_VAULT_NAMES.items():
        if provider_id in resolved:
            continue
        url_patterns = PROVIDER_VAULT_URLS.get(provider_id, [])
        candidates: list[tuple[int, str, int]] = []
        for row in metadata:
            score = _provider_secret_match_score(
                provider_id,
                str(row["name"] or ""),
                str(row["url"] or ""),
                names,
                url_patterns,
            )
            if score <= 0:
                continue
            recency = str(row["updated_at"] or row["created_at"] or "")
            candidates.append((score, recency, int(row["id"])))
        for _score, _recency, secret_id in sorted(candidates, key=lambda item: (item[0], item[1], item[2]), reverse=True):
            secret = vault_get_secret(secret_id, key)
            if secret and secret.get("password"):
                resolved[provider_id] = str(secret["password"])
                break
    return resolved


def vault_provider_key_status() -> dict[str, object]:
    resolved: dict[str, bool] = {}
    if VaultSession.is_unlocked():
        for provider_id in vault_resolve_all_provider_keys():
            resolved[provider_id] = True
    return {"unlocked": VaultSession.is_unlocked(), "resolved": resolved, "dev_bypass": False}




def enable_auto_unlock() -> None:
    from urllib.parse import urlparse

    forced = os.environ.get("AXON_WATCH_REMOTELY_REACHABLE", "").strip().lower()
    public = os.environ.get("AXON_WATCH_PUBLIC_BASE_URL", "http://127.0.0.1:4173").strip()
    host = (urlparse(public).hostname or "").lower()
    loopback = host in {"127.0.0.1", "localhost", "::1"}
    remotely = forced in {"1", "true", "yes", "on"} or (
        forced not in {"0", "false", "no", "off"} and not loopback
    )
    if remotely:
        raise RuntimeError(
            "Vault auto-unlock is disabled when the deployment is remotely reachable"
        )
    key = VaultSession.get_key()
    if key is None:
        raise RuntimeError("Vault must be unlocked first")
    save_auto_unlock_keyfile(key)


def disable_auto_unlock() -> bool:
    return remove_auto_unlock_keyfile()


def attempt_auto_unlock() -> tuple[bool, str]:
    from urllib.parse import urlparse

    if VaultSession.is_unlocked():
        return True, "Already unlocked"
    forced = os.environ.get("AXON_WATCH_REMOTELY_REACHABLE", "").strip().lower()
    public = os.environ.get("AXON_WATCH_PUBLIC_BASE_URL", "http://127.0.0.1:4173").strip()
    host = (urlparse(public).hostname or "").lower()
    loopback = host in {"127.0.0.1", "localhost", "::1"}
    remotely = forced in {"1", "true", "yes", "on"} or (
        forced not in {"0", "false", "no", "off"} and not loopback
    )
    if remotely:
        return False, "Auto-unlock refused (remotely reachable deployment)"
    if not auto_unlock_enabled():
        return False, "No auto-unlock keyfile"
    vault_key = load_auto_unlock_keyfile()
    if vault_key is None:
        return False, "Failed to decrypt keyfile"
    with vault_connection() as conn:
        enc_totp = get_setting(conn, "vault_totp_enc")
        if not enc_totp:
            return False, "Vault not set up"
        try:
            decrypt(enc_totp, vault_key)
        except Exception:
            remove_auto_unlock_keyfile()
            return False, "Keyfile invalid (master password changed?). Auto-unlock disabled."
    VaultSession.unlock(vault_key, session_ttl=VaultSession.EXTENDED_TTL)
    migrate_legacy_import_file()
    return True, "Vault auto-unlocked"


def migrate_legacy_import_file() -> list[str]:
    """Import Phase F vault-import.json keys into encrypted vault as login secrets."""
    if not VaultSession.is_unlocked():
        return []
    key = VaultSession.get_key()
    if key is None:
        return []
    imported = load_vault_import()
    if not imported:
        return []
    migrated: list[str] = []
    for name, value in imported.items():
        if not str(name).strip() or not str(value).strip():
            continue
        if vault_find_by_name(str(name)):
            continue
        vault_add_secret(key, str(name), "key", "", str(value), "", "Migrated from vault-import.json")
        migrated.append(str(name))
    return migrated


def vault_runtime_env() -> dict[str, str]:
    from app.vault import runtime_env as _runtime_env

    return _runtime_env.vault_runtime_env()


def vault_runtime_posture() -> dict[str, object]:
    from app.vault import runtime_env as _runtime_env

    return _runtime_env.vault_runtime_posture()
