"""Encrypted vault backup export/import (Signal-compatible)."""

from __future__ import annotations

import base64
import json
import os
import secrets
from datetime import datetime, timezone
from typing import Any

from app.vault.crypto import decrypt, derive_key, encrypt

BACKUP_FORMAT = "axon-vault-backup-v1"
BACKUP_EXTENSION = ".axonvault"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalize_secret_row(row: dict[str, Any]) -> dict[str, str]:
    return {
        "name": str(row.get("name") or "").strip(),
        "category": str(row.get("category") or "general").strip() or "general",
        "username": str(row.get("username") or "").strip(),
        "password": str(row.get("password") or "").strip(),
        "url": str(row.get("url") or "").strip(),
        "notes": str(row.get("notes") or "").strip(),
    }


def build_backup_payload(secrets: list[dict[str, Any]], *, source_host: str = "") -> dict[str, Any]:
    cleaned = [normalize_secret_row(item) for item in secrets if str(item.get("name") or "").strip()]
    cleaned.sort(key=lambda item: item["name"].lower())
    return {
        "format": BACKUP_FORMAT,
        "exported_at": _utc_now_iso(),
        "source_host": str(source_host or "").strip(),
        "secret_count": len(cleaned),
        "secrets": cleaned,
    }


def encrypt_backup_payload(payload: dict[str, Any], backup_password: str) -> str:
    password = str(backup_password or "").strip()
    if len(password) < 8:
        raise ValueError("Backup password must be at least 8 characters.")
    salt = os.urandom(16)
    key = derive_key(password, salt)
    envelope = {
        "format": BACKUP_FORMAT,
        "kdf": "pbkdf2-sha256",
        "iterations": 480_000,
        "salt": base64.b64encode(salt).decode("ascii"),
        "ciphertext": encrypt(json.dumps(payload, separators=(",", ":"), sort_keys=True), key),
    }
    return json.dumps(envelope, separators=(",", ":"), sort_keys=True)


def decrypt_backup_file(raw_text: str, backup_password: str) -> dict[str, Any]:
    password = str(backup_password or "").strip()
    if len(password) < 8:
        raise ValueError("Backup password must be at least 8 characters.")
    try:
        envelope = json.loads(str(raw_text or ""))
    except json.JSONDecodeError as exc:
        raise ValueError("Backup file is not valid JSON.") from exc
    if not isinstance(envelope, dict):
        raise ValueError("Backup file format is invalid.")
    if str(envelope.get("format") or "") != BACKUP_FORMAT:
        raise ValueError(f"Unsupported backup format: {envelope.get('format') or 'unknown'}")
    salt_b64 = str(envelope.get("salt") or "").strip()
    ciphertext = str(envelope.get("ciphertext") or "").strip()
    if not salt_b64 or not ciphertext:
        raise ValueError("Backup file is missing encryption metadata.")
    salt = base64.b64decode(salt_b64.encode("ascii"))
    key = derive_key(password, salt)
    try:
        plaintext = decrypt(ciphertext, key)
        payload = json.loads(plaintext)
    except Exception as exc:
        raise ValueError("Backup password is incorrect or the file is corrupted.") from exc
    if not isinstance(payload, dict) or str(payload.get("format") or "") != BACKUP_FORMAT:
        raise ValueError("Decrypted backup payload is invalid.")
    secrets_list = payload.get("secrets")
    if not isinstance(secrets_list, list):
        raise ValueError("Decrypted backup payload is missing secrets.")
    return payload


def suggested_backup_filename() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    token = secrets.token_hex(3)
    return f"axon-vault-backup-{stamp}-{token}{BACKUP_EXTENSION}"
