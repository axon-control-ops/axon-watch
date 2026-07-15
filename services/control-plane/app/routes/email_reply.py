"""Email reply-suggestion routes for the operator console."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.email_reply_suggest import suggest_email_reply

router = APIRouter(tags=["email-reply"])


class EmailSuggestReplyRequest(BaseModel):
    subject: str = ""
    sender: str = ""
    text: str = ""
    operator_name: str = "Axon operator"


@router.post("/api/email/suggest-reply")
def email_suggest_reply(body: EmailSuggestReplyRequest) -> dict[str, Any]:
    return suggest_email_reply(
        subject=body.subject,
        sender=body.sender,
        text=body.text,
        operator_name=body.operator_name or "Axon operator",
    )
