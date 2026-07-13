"""Operator email settings and mailbox management routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.email_mailbox_probe import probe_imap, probe_smtp
from app.persistence import email_settings_store
from app.vault import routes as vault_routes

router = APIRouter(tags=["email-settings"])


class EmailSettingsPatchRequest(BaseModel):
    bridge_enabled: bool | None = None
    bridge_workspace_id: str | None = None
    stub_enabled: bool | None = None
    workspace_hint_map: dict[str, str] | None = None


class EmailAccountUpsertRequest(BaseModel):
    account_id: str | None = None
    workspace_id: str
    email_address: str
    display_name: str = ""
    imap_host: str = ""
    imap_port: int = 993
    imap_username: str = ""
    imap_ssl: bool = True
    imap_folder: str = "INBOX"
    smtp_host: str = ""
    smtp_port: int = 465
    smtp_username: str = ""
    smtp_ssl: bool = True
    smtp_starttls: bool = False
    smtp_from_email: str = ""
    monitor_enabled: bool = True
    poll_seconds: int = 60
    password_imap: str = ""
    password_smtp: str = ""
    keep_existing_passwords: bool = True


class EmailAccountTestRequest(BaseModel):
    account_id: str | None = None
    password_imap: str = ""
    password_smtp: str = ""
    account: dict[str, Any] | None = None


def _vault_unlocked() -> bool:
    try:
        status = vault_routes.get_vault_status()
        vault = status.get("vault") if isinstance(status, dict) else None
        if isinstance(vault, dict):
            # Watch vault snapshot uses is_unlocked; keep unlocked as a fallback alias.
            return bool(vault.get("is_unlocked") or vault.get("unlocked"))
    except Exception:  # noqa: BLE001
        return False
    return False


def _find_secret_id_by_name(name: str) -> int | None:
    try:
        secrets = vault_routes.list_vault_secrets()
    except Exception:  # noqa: BLE001
        return None
    target = str(name or "").strip()
    for row in secrets:
        if not isinstance(row, dict):
            continue
        if str(row.get("name") or "").strip() == target:
            try:
                return int(row.get("id"))
            except (TypeError, ValueError):
                return None
    return None


def _upsert_vault_password(*, name: str, password: str, username: str, notes: str) -> str:
    existing_id = _find_secret_id_by_name(name)
    body = {
        "name": name,
        "category": "email",
        "username": username,
        "password": password,
        "url": "",
        "notes": notes,
    }
    if existing_id is not None:
        vault_routes.update_vault_secret(existing_id, body)
    else:
        vault_routes.create_vault_secret(body)
    return f"vault:{name}"


def _resolve_vault_password(password_ref: str) -> str:
    ref = str(password_ref or "").strip()
    if not ref:
        return ""
    name = ref[6:] if ref.startswith("vault:") else ref
    secret_id = _find_secret_id_by_name(name)
    if secret_id is None:
        return ""
    try:
        detail = vault_routes.get_vault_secret(secret_id)
    except Exception:  # noqa: BLE001
        return ""
    if isinstance(detail, dict):
        return str(detail.get("password") or "").strip()
    return ""


def _status_payload(settings: dict[str, Any]) -> dict[str, Any]:
    accounts = settings.get("accounts") or []
    return {
        "settings": settings,
        "auth": {
            "configured": len(accounts) > 0,
            "account_count": len(accounts),
            "locked": not _vault_unlocked(),
            "bridge_enabled": bool(settings.get("bridge_enabled")),
            "stub_enabled": bool(settings.get("stub_enabled", True)),
        },
        "projection_path": str(email_settings_store.projection_path()),
    }


@router.get("/api/email/settings")
def email_settings_get() -> dict[str, Any]:
    settings = email_settings_store.load_settings()
    return _status_payload(settings)


@router.patch("/api/email/settings")
def email_settings_patch(body: EmailSettingsPatchRequest) -> dict[str, Any]:
    current = email_settings_store.load_settings()
    patch = body.model_dump(exclude_none=True)
    current.update(patch)
    saved = email_settings_store.save_settings(current)
    return _status_payload(saved["settings"])


@router.post("/api/email/accounts")
def email_accounts_upsert(body: EmailAccountUpsertRequest) -> dict[str, Any]:
    email_address = body.email_address.strip()
    workspace_id = body.workspace_id.strip()
    if not email_address or not workspace_id:
        raise HTTPException(status_code=400, detail="email_address and workspace_id are required")

    imap_ref = ""
    smtp_ref = ""
    password_warning: str | None = None
    wants_passwords = bool(body.password_imap.strip() or body.password_smtp.strip())
    vault_ready = _vault_unlocked()

    if wants_passwords and not vault_ready:
        # Save hosts/config anyway so the mailbox appears; passwords can be added after unlock.
        password_warning = (
            "Mailbox saved without passwords. Unlock Axon-X Vault (top bar → VAULT), "
            "then edit this mailbox and save passwords."
        )
    elif body.password_imap.strip():
        try:
            imap_ref = _upsert_vault_password(
                name=email_settings_store.vault_secret_name(
                    workspace_id=workspace_id, email_address=email_address, kind="imap"
                ),
                password=body.password_imap.strip(),
                username=body.imap_username.strip() or email_address,
                notes=f"IMAP password for {email_address}",
            )
        except RuntimeError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    smtp_password = body.password_smtp.strip() or (
        body.password_imap.strip() if vault_ready else ""
    )
    if smtp_password and vault_ready:
        try:
            smtp_ref = _upsert_vault_password(
                name=email_settings_store.vault_secret_name(
                    workspace_id=workspace_id, email_address=email_address, kind="smtp"
                ),
                password=smtp_password,
                username=body.smtp_username.strip() or email_address,
                notes=f"SMTP password for {email_address}",
            )
        except RuntimeError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    account_payload = {
        "account_id": body.account_id,
        "workspace_id": workspace_id,
        "email_address": email_address,
        "display_name": body.display_name.strip() or email_address,
        "imap": {
            "host": body.imap_host.strip(),
            "port": body.imap_port,
            "username": body.imap_username.strip() or email_address,
            "ssl": body.imap_ssl,
            "folder": body.imap_folder.strip() or "INBOX",
            "password_ref": imap_ref,
        },
        "smtp": {
            "host": body.smtp_host.strip(),
            "port": body.smtp_port,
            "username": body.smtp_username.strip() or email_address,
            "ssl": body.smtp_ssl,
            "starttls": body.smtp_starttls,
            "from_email": body.smtp_from_email.strip() or email_address,
            "password_ref": smtp_ref,
        },
        "monitor": {
            "enabled": body.monitor_enabled,
            "poll_seconds": body.poll_seconds,
        },
    }
    try:
        result = email_settings_store.upsert_account(account_payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    payload = _status_payload(result["settings"])
    payload["account"] = result.get("account")
    if password_warning:
        payload["warning"] = password_warning
    return payload


@router.delete("/api/email/accounts/{account_id}")
def email_accounts_delete(account_id: str) -> dict[str, Any]:
    try:
        result = email_settings_store.delete_account(account_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _status_payload(result["settings"])


@router.post("/api/email/accounts/test")
def email_accounts_test(body: EmailAccountTestRequest) -> dict[str, Any]:
    settings = email_settings_store.load_settings()
    account: dict[str, Any] | None = None
    if body.account_id:
        for entry in settings.get("accounts") or []:
            if str(entry.get("account_id")) == str(body.account_id):
                account = entry
                break
    elif isinstance(body.account, dict):
        account = email_settings_store.normalize_account(body.account)

    if account is None:
        raise HTTPException(status_code=404, detail="mailbox account not found")

    imap_password = body.password_imap.strip()
    smtp_password = body.password_smtp.strip() or imap_password
    if not imap_password:
        imap_password = _resolve_vault_password(str(account.get("imap", {}).get("password_ref") or ""))
    if not smtp_password:
        smtp_password = _resolve_vault_password(str(account.get("smtp", {}).get("password_ref") or "")) or imap_password

    if not imap_password and not smtp_password:
        raise HTTPException(
            status_code=409,
            detail="Provide passwords or unlock the vault with saved mailbox secrets.",
        )

    imap_result = probe_imap(account, imap_password) if imap_password else {
        "ok": False,
        "detail": "IMAP password missing.",
    }
    smtp_result = probe_smtp(account, smtp_password) if smtp_password else {
        "ok": False,
        "detail": "SMTP password missing.",
    }
    return {
        "ok": bool(imap_result.get("ok")) and bool(smtp_result.get("ok")),
        "imap": imap_result,
        "smtp": smtp_result,
        "account_id": account.get("account_id"),
        "email_address": account.get("email_address"),
    }
