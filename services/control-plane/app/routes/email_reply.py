"""Email reply-suggestion and approval-gated send routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.email_account_resolve import resolve_workspace_email_account
from app.email_reply_suggest import suggest_email_reply
from app.email_smtp_send import EmailSendError, send_smtp_message
from app.persistence import email_settings_store
from app.routes import email_settings as email_settings_routes

router = APIRouter(tags=["email-reply"])


class EmailSuggestReplyRequest(BaseModel):
    subject: str = ""
    sender: str = ""
    text: str = ""
    operator_name: str = ""


class EmailSendRequest(BaseModel):
    to: str
    subject: str
    body: str
    workspace_id: str = ""
    account_id: str = ""
    confirm_send: bool = False
    password_smtp: str = ""


@router.post("/api/email/suggest-reply")
def email_suggest_reply(body: EmailSuggestReplyRequest) -> dict[str, Any]:
    return suggest_email_reply(
        subject=body.subject,
        sender=body.sender,
        text=body.text,
        operator_name=body.operator_name,
    )


@router.post("/api/email/send")
def email_send(body: EmailSendRequest) -> dict[str, Any]:
    if not body.confirm_send:
        raise HTTPException(
            status_code=400,
            detail="Set confirm_send=true after reviewing the draft. Sends are never automatic.",
        )
    settings = email_settings_store.load_settings()
    account = resolve_workspace_email_account(
        settings,
        workspace_id=body.workspace_id,
        account_id=body.account_id,
    )
    if account is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "No mailbox configured for this workspace. "
                "Add the workspace email under Settings → Email."
            ),
        )

    password = body.password_smtp.strip()
    if not password:
        smtp = account.get("smtp") if isinstance(account.get("smtp"), dict) else {}
        imap = account.get("imap") if isinstance(account.get("imap"), dict) else {}
        password = email_settings_routes._resolve_vault_password(
            str(smtp.get("password_ref") or "")
        ) or email_settings_routes._resolve_vault_password(
            str(imap.get("password_ref") or "")
        )
    if not password:
        raise HTTPException(
            status_code=409,
            detail=(
                "Unlock Axon-X Vault and save the mailbox password under "
                "Settings → Email before sending."
            ),
        )

    try:
        return send_smtp_message(
            account,
            password=password,
            to_address=body.to,
            subject=body.subject,
            body_text=body.body,
            confirm_send=True,
        )
    except EmailSendError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
