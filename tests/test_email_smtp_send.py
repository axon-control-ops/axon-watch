"""Approval-gated SMTP send tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
if str(CONTROL_PLANE_ROOT) not in sys.path:
    sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.email_smtp_send import EmailSendError, send_smtp_message  # noqa: E402


ACCOUNT = {
    "account_id": "acct-1",
    "email_address": "ops@example.com",
    "smtp": {
        "host": "smtp.example.com",
        "port": 465,
        "ssl": True,
        "username": "ops@example.com",
        "from_email": "ops@example.com",
    },
}


class EmailSmtpSendTests(unittest.TestCase):
    def test_requires_confirm_send(self) -> None:
        with self.assertRaises(EmailSendError):
            send_smtp_message(
                ACCOUNT,
                password="secret",
                to_address="user@example.com",
                subject="Hello",
                body_text="Body",
                confirm_send=False,
            )

    def test_send_uses_smtp_ssl(self) -> None:
        client = MagicMock()
        client.send_message.return_value = {}
        with patch("app.email_smtp_send.smtplib.SMTP_SSL", return_value=client) as smtp_ssl:
            result = send_smtp_message(
                ACCOUNT,
                password="secret",
                to_address="user@example.com",
                subject="Hello",
                body_text="Body text",
                confirm_send=True,
            )
        smtp_ssl.assert_called_once()
        client.login.assert_called_once_with("ops@example.com", "secret")
        client.send_message.assert_called_once()
        client.quit.assert_called_once()
        self.assertTrue(result["ok"])
        self.assertEqual("user@example.com", result["to"])
        self.assertEqual("Hello", result["subject"])
        self.assertTrue(str(result["message_id"]).startswith("<"))


if __name__ == "__main__":
    unittest.main()
