"""Control-plane vault routes (operator-facing proxy to axon-watch)."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

from app.vault import watch_adapter


def get_vault_status() -> dict[str, Any]:
    return {"vault": watch_adapter.fetch_watch_vault_snapshot()}


def import_vault_monitor_keys(secrets: dict[str, str], *, export_text: str = "") -> dict[str, Any]:
    cleaned = {
        str(key).strip(): str(value).strip()
        for key, value in secrets.items()
        if str(key).strip() and str(value).strip()
    }
    result = watch_adapter.post_watch_vault_monitor_import(cleaned, export_text=export_text)
    snapshot = watch_adapter.fetch_watch_vault_snapshot()
    return {"vault_import": result, "vault": snapshot}


def vault_setup(master_password: str) -> dict[str, Any]:
    return watch_adapter.request_json(
        "POST",
        "/internal/watch/vault/setup",
        payload={"master_password": master_password},
    )


def vault_unlock(master_password: str, totp_code: str, *, remember_me: bool = False) -> dict[str, Any]:
    return watch_adapter.request_json(
        "POST",
        "/internal/watch/vault/unlock",
        payload={
            "master_password": master_password,
            "totp_code": totp_code,
            "remember_me": remember_me,
        },
    )


def vault_lock() -> dict[str, Any]:
    return watch_adapter.request_json("POST", "/internal/watch/vault/lock")


def vault_auto_unlock_status() -> dict[str, Any]:
    return watch_adapter.request_json("GET", "/internal/watch/vault/auto-unlock/status")


def vault_auto_unlock_enable() -> dict[str, Any]:
    return watch_adapter.request_json("POST", "/internal/watch/vault/auto-unlock/enable")


def vault_auto_unlock_disable() -> dict[str, Any]:
    return watch_adapter.request_json("POST", "/internal/watch/vault/auto-unlock/disable")


def vault_provider_keys() -> dict[str, Any]:
    return watch_adapter.request_json("GET", "/internal/watch/vault/provider-keys")


def list_vault_secrets() -> list[dict[str, Any]]:
    payload = watch_adapter.request_json("GET", "/internal/watch/vault/secrets")
    if not isinstance(payload, list):
        raise RuntimeError("watch vault secrets response was not a list")
    return payload


def get_vault_secret(secret_id: int) -> dict[str, Any]:
    return watch_adapter.request_json("GET", f"/internal/watch/vault/secrets/{secret_id}")


def create_vault_secret(body: dict[str, Any]) -> dict[str, Any]:
    return watch_adapter.request_json("POST", "/internal/watch/vault/secrets", payload=body)


def update_vault_secret(secret_id: int, body: dict[str, Any]) -> dict[str, Any]:
    return watch_adapter.request_json("PUT", f"/internal/watch/vault/secrets/{secret_id}", payload=body)


def delete_vault_secret(secret_id: int) -> dict[str, Any]:
    return watch_adapter.request_json("DELETE", f"/internal/watch/vault/secrets/{secret_id}")


def export_vault_backup(backup_password: str) -> tuple[bytes, dict[str, str]]:
    return watch_adapter.request_bytes(
        "POST",
        "/internal/watch/vault/export",
        payload={"backup_password": backup_password},
    )


def export_vault_csv(format: str = "axon") -> tuple[bytes, dict[str, str]]:
    query = urlencode({"format": format})
    return watch_adapter.request_bytes("GET", f"/internal/watch/vault/export/csv?{query}")


def import_vault_backup(
    *,
    file_bytes: bytes,
    filename: str,
    backup_password: str = "",
    mode: str = "merge",
) -> dict[str, Any]:
    return watch_adapter.post_watch_vault_backup_import(
        file_bytes=file_bytes,
        filename=filename,
        backup_password=backup_password,
        mode=mode,
    )


# Backward-compatible alias for Phase F monitor import
import_vault_secrets = import_vault_monitor_keys
