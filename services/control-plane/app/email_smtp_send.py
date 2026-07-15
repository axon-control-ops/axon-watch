"""Approval-gated SMTP send for operator email replies."""

from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage
from email.utils import make_msgid
from typing import Any


class EmailSendError(ValueError):
    pass


def send_smtp_message(
    account: dict[str, Any],
    *,
    password: str,
    to_address: str,
    subject: str,
    body_text: str,
    confirm_send: bool,
) -> dict[str, Any]:
    if not confirm_send:
        raise EmailSendError("confirm_send must be true to send mail")
    to_address = str(to_address or "").strip()
    subject = str(subject or "").strip()
    body_text = str(body_text or "").rstrip() + "\n"
    if not to_address or "@" not in to_address:
        raise EmailSendError("valid to address is required")
    if not subject:
        raise EmailSendError("subject is required")
    if not body_text.strip():
        raise EmailSendError("body is required")

    smtp = account.get("smtp") if isinstance(account.get("smtp"), dict) else {}
    host = str(smtp.get("host") or "").strip()
    port = int(smtp.get("port") or 465)
    username = str(smtp.get("username") or account.get("email_address") or "").strip()
    from_email = str(smtp.get("from_email") or username).strip()
    use_ssl = bool(smtp.get("ssl", port == 465))
    use_starttls = bool(smtp.get("starttls", False))
    password = str(password or "").strip()
    if not host or not username or not password:
        raise EmailSendError("SMTP host, username, and password are required")

    message = EmailMessage()
    message["From"] = from_email
    message["To"] = to_address
    message["Subject"] = subject
    message["Message-ID"] = make_msgid()
    message.set_content(body_text)

    client: smtplib.SMTP | smtplib.SMTP_SSL | None = None
    try:
        if use_ssl:
            context = ssl.create_default_context()
            client = smtplib.SMTP_SSL(host, port, timeout=20, context=context)
        else:
            client = smtplib.SMTP(host, port, timeout=20)
            client.ehlo()
            if use_starttls:
                context = ssl.create_default_context()
                client.starttls(context=context)
                client.ehlo()
        client.login(username, password)
        refused = client.send_message(message)
    except Exception as exc:  # noqa: BLE001
        raise EmailSendError(f"SMTP send failed: {exc}") from exc
    finally:
        if client is not None:
            try:
                client.quit()
            except Exception:  # noqa: BLE001
                pass

    return {
        "ok": True,
        "from": from_email,
        "to": to_address,
        "subject": subject,
        "message_id": str(message["Message-ID"]),
        "account_id": account.get("account_id"),
        "email_address": account.get("email_address"),
        "refused": refused or {},
    }
