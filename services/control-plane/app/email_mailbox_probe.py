"""IMAP/SMTP connection probes for operator email settings."""

from __future__ import annotations

import imaplib
import smtplib
import ssl
from typing import Any


def probe_imap(account: dict[str, Any], password: str) -> dict[str, Any]:
    imap = account.get("imap") if isinstance(account.get("imap"), dict) else {}
    host = str(imap.get("host") or "").strip()
    port = int(imap.get("port") or 993)
    username = str(imap.get("username") or account.get("email_address") or "").strip()
    folder = str(imap.get("folder") or "INBOX").strip() or "INBOX"
    use_ssl = bool(imap.get("ssl", True))
    if not host or not username or not password:
        return {"ok": False, "detail": "IMAP host, username, and password are required."}

    client: imaplib.IMAP4 | imaplib.IMAP4_SSL | None = None
    try:
        if use_ssl:
            client = imaplib.IMAP4_SSL(host, port, timeout=12)
        else:
            client = imaplib.IMAP4(host, port, timeout=12)
        status, _ = client.login(username, password)
        if status != "OK":
            return {"ok": False, "detail": f"IMAP login failed ({status})."}
        select_status, data = client.select(folder, readonly=True)
        if select_status != "OK":
            return {"ok": False, "detail": f"IMAP folder select failed for {folder}."}
        count = 0
        if data and data[0]:
            try:
                count = int(data[0])
            except (TypeError, ValueError):
                count = 0
        return {
            "ok": True,
            "detail": f"IMAP OK — {folder} selected ({count} messages).",
            "folder": folder,
            "message_count": count,
        }
    except Exception as exc:  # noqa: BLE001 — surface probe errors to operator
        return {"ok": False, "detail": f"IMAP probe failed: {exc}"}
    finally:
        if client is not None:
            try:
                client.logout()
            except Exception:  # noqa: BLE001
                pass


def probe_smtp(account: dict[str, Any], password: str) -> dict[str, Any]:
    smtp = account.get("smtp") if isinstance(account.get("smtp"), dict) else {}
    host = str(smtp.get("host") or "").strip()
    port = int(smtp.get("port") or 465)
    username = str(smtp.get("username") or account.get("email_address") or "").strip()
    use_ssl = bool(smtp.get("ssl", port == 465))
    use_starttls = bool(smtp.get("starttls", False))
    if not host or not username or not password:
        return {"ok": False, "detail": "SMTP host, username, and password are required."}

    client: smtplib.SMTP | smtplib.SMTP_SSL | None = None
    try:
        if use_ssl:
            context = ssl.create_default_context()
            client = smtplib.SMTP_SSL(host, port, timeout=12, context=context)
        else:
            client = smtplib.SMTP(host, port, timeout=12)
            client.ehlo()
            if use_starttls:
                context = ssl.create_default_context()
                client.starttls(context=context)
                client.ehlo()
        client.login(username, password)
        return {"ok": True, "detail": "SMTP OK — authenticated."}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "detail": f"SMTP probe failed: {exc}"}
    finally:
        if client is not None:
            try:
                client.quit()
            except Exception:  # noqa: BLE001
                pass
