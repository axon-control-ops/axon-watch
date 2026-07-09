"""Vault HTTP routes."""

from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response

from app.routes.schemas import (
    VaultExportRequest,
    VaultImportRequest,
    VaultSecretRequest,
    VaultSetupRequest,
    VaultUnlockRequest,
)
from app.vault.routes import (
    create_vault_secret,
    delete_vault_secret,
    export_vault_backup,
    export_vault_csv,
    get_vault_secret,
    get_vault_status,
    import_vault_backup,
    import_vault_monitor_keys,
    list_vault_secrets,
    update_vault_secret,
    vault_auto_unlock_disable,
    vault_auto_unlock_enable,
    vault_auto_unlock_status,
    vault_lock,
    vault_provider_keys,
    vault_setup,
    vault_unlock,
)

router = APIRouter()


def _vault_http_error(exc: RuntimeError) -> HTTPException:
    message = str(exc)
    for code in (401, 423, 400, 404):
        if f"HTTP {code}" in message:
            detail = message.split(": ", 1)[-1] if ": " in message else message
            return HTTPException(status_code=code, detail=detail)
    return HTTPException(status_code=503, detail=message)


@router.get("/api/vault/status")
def vault_status_route() -> dict[str, object]:
    try:
        return get_vault_status()
    except RuntimeError as exc:
        raise _vault_http_error(exc) from exc


@router.get("/api/vault/provider-keys")
def vault_provider_keys_route() -> dict[str, object]:
    try:
        return vault_provider_keys()
    except RuntimeError as exc:
        raise _vault_http_error(exc) from exc


@router.post("/api/vault/setup")
def vault_setup_route(body: VaultSetupRequest) -> dict[str, object]:
    try:
        return vault_setup(body.master_password)
    except RuntimeError as exc:
        raise _vault_http_error(exc) from exc


@router.post("/api/vault/unlock")
def vault_unlock_route(body: VaultUnlockRequest) -> dict[str, object]:
    try:
        return vault_unlock(body.master_password, body.totp_code, remember_me=body.remember_me)
    except RuntimeError as exc:
        raise _vault_http_error(exc) from exc


@router.post("/api/vault/lock")
def vault_lock_route() -> dict[str, object]:
    try:
        return vault_lock()
    except RuntimeError as exc:
        raise _vault_http_error(exc) from exc


@router.get("/api/vault/auto-unlock/status")
def vault_auto_unlock_status_route() -> dict[str, object]:
    try:
        return vault_auto_unlock_status()
    except RuntimeError as exc:
        raise _vault_http_error(exc) from exc


@router.post("/api/vault/auto-unlock/enable")
def vault_auto_unlock_enable_route() -> dict[str, object]:
    try:
        return vault_auto_unlock_enable()
    except RuntimeError as exc:
        raise _vault_http_error(exc) from exc


@router.post("/api/vault/auto-unlock/disable")
def vault_auto_unlock_disable_route() -> dict[str, object]:
    try:
        return vault_auto_unlock_disable()
    except RuntimeError as exc:
        raise _vault_http_error(exc) from exc


@router.get("/api/vault/secrets")
def vault_secrets_list_route() -> list[dict[str, object]]:
    try:
        return list_vault_secrets()
    except RuntimeError as exc:
        raise _vault_http_error(exc) from exc


@router.get("/api/vault/secrets/{secret_id}")
def vault_secrets_show_route(secret_id: int) -> dict[str, object]:
    try:
        return get_vault_secret(secret_id)
    except RuntimeError as exc:
        raise _vault_http_error(exc) from exc


@router.post("/api/vault/secrets")
def vault_secrets_create_route(body: VaultSecretRequest) -> dict[str, object]:
    try:
        return create_vault_secret(body.model_dump())
    except RuntimeError as exc:
        raise _vault_http_error(exc) from exc


@router.put("/api/vault/secrets/{secret_id}")
def vault_secrets_update_route(secret_id: int, body: VaultSecretRequest) -> dict[str, object]:
    try:
        return update_vault_secret(secret_id, body.model_dump())
    except RuntimeError as exc:
        raise _vault_http_error(exc) from exc


@router.delete("/api/vault/secrets/{secret_id}")
def vault_secrets_delete_route(secret_id: int) -> dict[str, object]:
    try:
        return delete_vault_secret(secret_id)
    except RuntimeError as exc:
        raise _vault_http_error(exc) from exc


@router.post("/api/vault/export")
def vault_export_backup_route(body: VaultExportRequest):
    try:
        content, headers = export_vault_backup(body.backup_password)
    except RuntimeError as exc:
        raise _vault_http_error(exc) from exc
    disposition = headers.get("content-disposition", "")
    media_type = headers.get("content-type", "application/json")
    response_headers = {"Content-Disposition": disposition} if disposition else {}
    return Response(content=content, media_type=media_type, headers=response_headers)


@router.get("/api/vault/export/csv")
def vault_export_csv_route(format: str = Query(default="axon")):
    try:
        content, headers = export_vault_csv(format)
    except RuntimeError as exc:
        raise _vault_http_error(exc) from exc
    disposition = headers.get("content-disposition", "")
    media_type = headers.get("content-type", "text/csv; charset=utf-8")
    response_headers = {"Content-Disposition": disposition} if disposition else {}
    return Response(content=content, media_type=media_type, headers=response_headers)


@router.post("/api/vault/import")
async def vault_import_backup_route(
    backup_password: str = Form(""),
    mode: str = Form("merge"),
    file: UploadFile = File(...),
) -> dict[str, object]:
    try:
        raw = await file.read()
        return import_vault_backup(
            file_bytes=raw,
            filename=str(file.filename or "vault-import.bin"),
            backup_password=backup_password,
            mode=mode,
        )
    except RuntimeError as exc:
        raise _vault_http_error(exc) from exc


@router.post("/api/vault/import/monitor-keys")
def vault_import_monitor_keys_route(body: VaultImportRequest) -> dict[str, object]:
    try:
        return import_vault_monitor_keys(body.secrets, export_text=body.export_text)
    except RuntimeError as exc:
        raise _vault_http_error(exc) from exc
