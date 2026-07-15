"""Workspace mailbox resolution tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
if str(CONTROL_PLANE_ROOT) not in sys.path:
    sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.email_account_resolve import resolve_workspace_email_account  # noqa: E402


SETTINGS = {
    "accounts": [
        {
            "account_id": "acct-axon",
            "workspace_id": "workspace_axon_watch",
            "email_address": "axonops@example.com",
        },
        {
            "account_id": "acct-dash",
            "workspace_id": "workspace_dashpro",
            "email_address": "superadmin@example.com",
        },
    ]
}


class EmailAccountResolveTests(unittest.TestCase):
    def test_prefers_workspace_mailbox(self) -> None:
        account = resolve_workspace_email_account(
            SETTINGS,
            workspace_id="workspace_dashpro",
            account_id="acct-axon",
        )
        assert account is not None
        self.assertEqual("acct-dash", account["account_id"])

    def test_falls_back_to_account_id(self) -> None:
        account = resolve_workspace_email_account(
            SETTINGS,
            workspace_id="workspace_missing",
            account_id="acct-axon",
        )
        assert account is not None
        self.assertEqual("acct-axon", account["account_id"])

    def test_returns_none_when_unconfigured(self) -> None:
        self.assertIsNone(
            resolve_workspace_email_account(
                SETTINGS,
                workspace_id="workspace_missing",
            )
        )


if __name__ == "__main__":
    unittest.main()
