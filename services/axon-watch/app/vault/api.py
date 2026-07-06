"""HTTP handlers for encrypted vault APIs (internal + operator proxy)."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from app.vault.backup import (
    build_backup_payload,
    decrypt_backup_file,
    encrypt_backup_payload,
    suggested_backup_filename,
)
from app.vault.csv_export import (
    collect_decrypted_secrets,
    secrets_to_axon_csv,
    secrets_to_bitwarden_csv,
    suggested_csv_filename,
)
from app.vault.csv_import import looks_like_axon_vault_csv, parse_axon_vault_csv
from app.vault.import_apply import import_vault_secrets
from app.vault.operations import (
    VaultSession,
    attempt_auto_unlock,
    disable_auto_unlock,
    enable_auto_unlock,
    lock_vault,
    migrate_legacy_import_file,
    setup_vault,
    unlock_vault,
    vault_add_secret,
    vault_delete_secret,
    vault_find_by_name,
    vault_get_secret,
    vault_is_setup,
    vault_list_secrets,
    vault_provider_key_status,
    vault_runtime_env,
    vault_runtime_posture,
    vault_status_core,
    vault_update_secret,
)
from app.vault.snapshot import vault_operator_snapshot


class VaultSetupBody(BaseModel):
    master_password: str


class VaultUnlockBody(BaseModel):
    master_password: str
    totp_code: str
    remember_me: bool = False


class VaultSecretBody(BaseModel):
    name: str
    category: str = "general"
    username: str = ""
    password: str = ""
    url: str = ""
    notes: str = ""


class VaultExportBody(BaseModel):
    backup_password: str


class VaultMonitorImportBody(BaseModel):
    secrets: dict[str, str] = {}
    export_text: str = ""


def _require_unlocked_key() -> bytes:
    key = VaultSession.get_key()
    if not key:
        raise HTTPException(423, "Vault is locked")
    return key


def handle_vault_status(*, project_root=None) -> dict[str, object]:
    attempt_auto_unlock()
    operator = vault_operator_snapshot(project_root=project_root)
    core = vault_status_core()
    return {"vault": {**core, **operator}}


def handle_vault_setup(body: VaultSetupBody) -> dict[str, object]:
    if vault_is_setup():
        raise HTTPException(400, "Vault is already set up. Reset not supported via API.")
    return setup_vault(body.master_password)


def handle_vault_unlock(body: VaultUnlockBody) -> dict[str, object]:
    ttl = VaultSession.EXTENDED_TTL if body.remember_me else VaultSession.DEFAULT_TTL
    ok, err = unlock_vault(body.master_password, body.totp_code, session_ttl=ttl)
    if not ok:
        raise HTTPException(401, err)
    migrated = migrate_legacy_import_file()
    return {
        "unlocked": True,
        "session_ttl": ttl,
        "ttl_label": "24 hours" if body.remember_me else "1 hour",
        "migrated_settings": migrated,
    }


def handle_vault_lock() -> dict[str, object]:
    lock_vault()
    return {"locked": True}


def handle_auto_unlock_status() -> dict[str, object]:
    from app.vault.session import auto_unlock_enabled

    return {"enabled": auto_unlock_enabled()}


def handle_auto_unlock_enable() -> dict[str, object]:
    try:
        enable_auto_unlock()
    except RuntimeError as exc:
        raise HTTPException(423, str(exc)) from exc
    return {"enabled": True, "message": "Auto-unlock will activate on next server start"}


def handle_auto_unlock_disable() -> dict[str, object]:
    removed = disable_auto_unlock()
    return {"enabled": False, "removed": removed}


def handle_provider_keys() -> dict[str, object]:
    return vault_provider_key_status()


def handle_runtime_posture() -> dict[str, object]:
    return {"vault_runtime": vault_runtime_posture()}


def handle_runtime_env() -> dict[str, object]:
    if not VaultSession.is_unlocked():
        return {"unlocked": False, "env": {}}
    return {"unlocked": True, "env": vault_runtime_env()}


def handle_list_secrets() -> list[dict[str, Any]]:
    if not VaultSession.is_unlocked():
        raise HTTPException(423, "Vault is locked")
    return vault_list_secrets()


def handle_get_secret(secret_id: int) -> dict[str, Any]:
    key = _require_unlocked_key()
    secret = vault_get_secret(secret_id, key)
    if not secret:
        raise HTTPException(404, "Secret not found")
    return secret


def handle_create_secret(body: VaultSecretBody) -> dict[str, object]:
    key = _require_unlocked_key()
    secret_id = vault_add_secret(
        key,
        body.name,
        body.category,
        body.username,
        body.password,
        body.url,
        body.notes,
    )
    return {"id": secret_id, "name": body.name}


def handle_update_secret(secret_id: int, body: VaultSecretBody) -> dict[str, object]:
    key = _require_unlocked_key()
    vault_update_secret(
        key,
        secret_id,
        body.name,
        body.category,
        body.username,
        body.password,
        body.url,
        body.notes,
    )
    return {"updated": True}


def handle_delete_secret(secret_id: int) -> dict[str, object]:
    if not VaultSession.is_unlocked():
        raise HTTPException(423, "Vault is locked")
    vault_delete_secret(secret_id)
    return {"deleted": True}


def handle_export_backup(body: VaultExportBody) -> Response:
    key = _require_unlocked_key()
    secrets = collect_decrypted_secrets(vault_list_secrets, vault_get_secret, key)
    payload = build_backup_payload(secrets)
    try:
        encrypted = encrypt_backup_payload(payload, body.backup_password)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    filename = suggested_backup_filename()
    return Response(
        content=encrypted,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def handle_export_csv(format: str = "axon") -> Response:
    key = _require_unlocked_key()
    normalized = str(format or "axon").strip().lower()
    if normalized not in {"axon", "bitwarden"}:
        raise HTTPException(400, "CSV format must be axon or bitwarden.")
    secrets = collect_decrypted_secrets(vault_list_secrets, vault_get_secret, key)
    csv_text = secrets_to_bitwarden_csv(secrets) if normalized == "bitwarden" else secrets_to_axon_csv(secrets)
    filename = suggested_csv_filename(normalized)  # type: ignore[arg-type]
    return Response(
        content=csv_text,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


async def handle_import_backup(
    *,
    backup_password: str = "",
    mode: str = "merge",
    file: UploadFile,
) -> dict[str, object]:
    key = _require_unlocked_key()
    normalized_mode = str(mode or "merge").strip().lower()
    if normalized_mode not in {"merge", "replace"}:
        raise HTTPException(400, "Import mode must be merge or replace.")
    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(400, "Backup file is empty.")
    if len(raw_bytes) > 5 * 1024 * 1024:
        raise HTTPException(400, "Backup file is too large (max 5 MB).")
    filename = str(file.filename or "").strip().lower()
    raw_text = raw_bytes.decode("utf-8")
    is_csv = filename.endswith(".csv") or looks_like_axon_vault_csv(raw_text)
    source_exported_at = ""
    source_secret_count = 0
    if is_csv:
        secrets = parse_axon_vault_csv(raw_text)
        if not secrets:
            raise HTTPException(400, "CSV file contains no secrets.")
        source_secret_count = len(secrets)
    else:
        if len(str(backup_password or "").strip()) < 8:
            raise HTTPException(400, "Backup password must be at least 8 characters.")
        try:
            payload = decrypt_backup_file(raw_text, backup_password)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        secrets = payload.get("secrets") or []
        if not isinstance(secrets, list) or not secrets:
            raise HTTPException(400, "Backup file contains no secrets.")
        source_exported_at = str(payload.get("exported_at") or "")
        source_secret_count = int(payload.get("secret_count") or len(secrets))

    counts = import_vault_secrets(
        list_by_name=vault_find_by_name,
        add_secret=vault_add_secret,
        update_secret=vault_update_secret,
        vault_key=key,
        secrets=secrets,
        mode=normalized_mode,  # type: ignore[arg-type]
    )
    return {
        "imported": True,
        "mode": normalized_mode,
        "format": "csv" if is_csv else "axonvault",
        "source_exported_at": source_exported_at,
        "source_secret_count": source_secret_count,
        **counts,
    }


def handle_monitor_import(body: VaultMonitorImportBody) -> dict[str, object]:
    from app.vault.credential_resolver import merge_vault_import
    from app.vault.csv_import import parse_vault_export_text
    from app.vault.snapshot import ALLOWED_IMPORT_KEYS

    secrets = dict(body.secrets)
    if body.export_text.strip():
        secrets.update(parse_vault_export_text(body.export_text))

    if VaultSession.is_unlocked():
        key = VaultSession.get_key()
        if key:
            imported_keys: list[str] = []
            for name, value in secrets.items():
                clean_name = str(name).strip()
                clean_value = str(value).strip()
                if not clean_name or not clean_value:
                    continue
                if clean_name not in ALLOWED_IMPORT_KEYS:
                    continue
                existing = vault_find_by_name(clean_name)
                if existing:
                    vault_update_secret(
                        key,
                        int(existing["id"]),
                        clean_name,
                        "key",
                        "",
                        clean_value,
                        "",
                        "",
                    )
                else:
                    vault_add_secret(key, clean_name, "key", "", clean_value, "", "")
                imported_keys.append(clean_name)
            return {"vault_import": {"imported_keys": sorted(imported_keys), "count": len(imported_keys)}}

    result = merge_vault_import(secrets, allowed_keys=ALLOWED_IMPORT_KEYS)
    return {"vault_import": result}
