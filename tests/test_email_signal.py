"""Email triage signal emission tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.support.watch_app_loader import load_watch_app, restore_app_modules


class EmailTriageTests(unittest.TestCase):
    def setUp(self) -> None:
        _watch_app, self._saved_modules = load_watch_app()
        from app.signals import email_signal as email_signal_module  # noqa: WPS433
        from app.signals.email_triage import analyze_email_message  # noqa: WPS433

        self.email_signal = email_signal_module
        self.analyze_email_message = analyze_email_message
        self.email_inbox_item = email_signal_module.email_inbox_item
        self.email_inbox_items = email_signal_module.email_inbox_items

    def tearDown(self) -> None:
        restore_app_modules(self._saved_modules)

    def test_analyze_email_message_extracts_actions_risks_and_commitments(self) -> None:
        analysis = self.analyze_email_message(
            {
                "subject": "Urgent: DashPro deploy failed",
                "text": (
                    "Please investigate the failing deploy today. "
                    "We cannot ship until this is fixed. "
                    "I will send the rollback plan tomorrow."
                ),
                "from": "CTO <cto@example.com>",
                "message_id": "<msg-1@example.com>",
            },
            workspace_names=["DashPro", "Axon"],
        )

        self.assertEqual(analysis["risk_level"], "high")
        self.assertGreaterEqual(analysis["priority"], 80)
        self.assertFalse(analysis["promotional"])
        self.assertTrue(analysis["action_requests"])
        self.assertTrue(analysis["risks"])
        self.assertTrue(analysis["commitments"])
        self.assertIn("DashPro", analysis["workspace_hints"])

    def test_analyze_email_message_downranks_promotional_deadline_copy(self) -> None:
        analysis = self.analyze_email_message(
            {
                "subject": "That app idea in your backlog now has a deadline",
                "text": (
                    "Shipaton 2026. 8 weeks, $1M in prizes. Starts August 1. "
                    "Pre-register on Devpost — we'll send you prize categories."
                ),
                "from": "Charlie Chapman <shipaton@revenuecat.com>",
                "message_id": "<promo@example.com>",
            }
        )

        self.assertTrue(analysis["promotional"])
        self.assertLessEqual(analysis["priority"], 40)
        self.assertEqual(analysis["risk_level"], "low")
        self.assertEqual(analysis["recommended_action"], "monitor_email")
        self.assertEqual(analysis["risks"], [])
        self.assertIsNone(
            self.email_inbox_item(analysis, workspace_id="workspace_dashpro")
        )

    def test_analyze_email_message_downranks_automated_billing_noreply(self) -> None:
        analysis = self.analyze_email_message(
            {
                "subject": "Your Microsoft invoice G170420650 is ready",
                "text": (
                    "Review your Microsoft invoice for King Martin. "
                    "Your statement is ready for review (see attached). Sign in to view it. "
                    "If you've already paid, disregard this email. "
                    "If paying by credit card, we'll automatically charge the card we have on file."
                ),
                "from": "Microsoft <microsoft-noreply@microsoft.com>",
                "message_id": "<invoice@microsoft.com>",
            }
        )

        self.assertTrue(analysis["automated_billing"])
        self.assertFalse(analysis["promotional"])
        self.assertLessEqual(analysis["priority"], 40)
        self.assertEqual(analysis["risk_level"], "low")
        self.assertEqual(analysis["recommended_action"], "monitor_email")
        self.assertEqual(analysis["action_requests"], [])
        self.assertEqual(analysis["commitments"], [])
        self.assertIsNone(
            self.email_inbox_item(analysis, workspace_id="workspace_dashpro")
        )

    def test_analyze_email_message_ignores_modal_may_as_due_marker(self) -> None:
        analysis = self.analyze_email_message(
            {
                "subject": "We're updating our Privacy Policy",
                "text": "You may review the updated Privacy Policy for more detail.",
                "from": "Anthropic Team <notice@email.anthropic.com>",
                "message_id": "<privacy@example.com>",
            }
        )

        self.assertNotIn("may", [marker.lower() for marker in analysis["due_markers"]])

        may_month = self.analyze_email_message(
            {
                "subject": "Invoice reminder",
                "text": "Please pay the balance by May 12.",
                "from": "Billing <billing@example.com>",
                "message_id": "<may-month@example.com>",
            }
        )
        self.assertIn("May", may_month["due_markers"])

    def test_email_inbox_item_requires_priority_threshold(self) -> None:
        low = self.analyze_email_message(
            {
                "subject": "Weekly digest",
                "text": "Here is this week's reading list.",
                "from": "Newsletter <news@example.com>",
                "message_id": "<low@example.com>",
            }
        )
        self.assertIsNone(self.email_inbox_item(low, workspace_id="workspace_axon_watch"))

        high = self.analyze_email_message(
            {
                "subject": "Urgent: DashPro deploy failed",
                "text": "Please investigate the failing deploy today. We cannot ship.",
                "from": "CTO <cto@example.com>",
                "message_id": "<high@example.com>",
            },
            workspace_names=["DashPro"],
        )
        item = self.email_inbox_item(high, workspace_id="workspace_axon_watch")
        assert item is not None
        self.assertEqual(item["source"], "email")
        self.assertEqual(item["meta"]["signal_family"], "email_triage")
        self.assertIn("sender", item["meta"])
        self.assertIn("recommended_action", item["meta"])

    def test_email_inbox_items_loads_stub_messages(self) -> None:
        stub = {
            "schema_version": 1,
            "enabled": True,
            "workspace_id": "workspace_axon_watch",
            "workspace_names": ["DashPro"],
            "messages": [
                {
                    "message_id": "<stub@example.com>",
                    "from": "CTO <cto@example.com>",
                    "subject": "Urgent: DashPro deploy failed",
                    "text": "Please investigate the failing deploy today. We cannot ship.",
                }
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "email-stub.json"
            path.write_text(json.dumps(stub), encoding="utf-8")
            with patch(
                "app.signals.email_signal.fetch_native_email_messages",
                return_value=None,
            ), patch("app.signals.email_signal._messages_from_live_bridge", return_value=None):
                items = self.email_inbox_items(stub_path=path)
        self.assertEqual(1, len(items))
        self.assertTrue(str(items[0]["signal_id"]).startswith("signal_email_"))
        self.assertEqual(items[0]["workspace_id"], "workspace_dashpro")
        self.assertIn("suggested_reply_body", items[0]["meta"])

    def test_email_inbox_items_prefers_native_imap(self) -> None:
        with patch(
            "app.signals.email_signal.fetch_native_email_messages",
            return_value=[
                {
                    "message_id": "<native@example.com>",
                    "account_id": "account-1",
                    "account_email": "operator@example.com",
                    "from": "Ops <ops@example.com>",
                    "subject": "Urgent: please fix DashPro today",
                    "text": "We cannot ship until this is fixed.",
                    "snippet": "We cannot ship until this is fixed.",
                }
            ],
        ), patch("app.signals.email_signal._messages_from_live_bridge", return_value=None):
            items = self.email_inbox_items()
        self.assertEqual(1, len(items))
        self.assertIn("suggested_reply_subject", items[0]["meta"])
        self.assertTrue(str(items[0]["meta"]["suggested_reply_subject"]).startswith("Re:"))
        self.assertEqual("account-1", items[0]["meta"]["email_account_id"])
        self.assertEqual("operator@example.com", items[0]["meta"]["email_account_address"])

    def test_email_inbox_items_use_mailbox_workspace_not_first_account_fallback(self) -> None:
        settings = {
            "bridge_enabled": False,
            "stub_enabled": False,
            "workspace_hint_map": {},
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
            ],
        }
        with patch(
            "app.signals.email_signal._load_operator_email_settings",
            return_value=settings,
        ), patch(
            "app.signals.email_signal.fetch_native_email_messages",
            return_value=[
                {
                    "message_id": "<superadmin-mail@example.com>",
                    "account_id": "acct-dash",
                    "account_email": "superadmin@example.com",
                    "from": "News <news@example.com>",
                    "subject": "No workspace keyword here",
                    "text": "Please review this invoice today. We cannot wait.",
                    "snippet": "Please review this invoice today. We cannot wait.",
                }
            ],
        ), patch("app.signals.email_signal._messages_from_live_bridge", return_value=None):
            items = self.email_inbox_items()
        self.assertEqual(1, len(items))
        self.assertEqual("workspace_dashpro", items[0]["workspace_id"])
        self.assertEqual("superadmin@example.com", items[0]["meta"]["email_account_address"])

    def test_resolve_email_workspace_id_from_hints(self) -> None:
        resolve_email_workspace_id = self.email_signal.resolve_email_workspace_id

        self.assertEqual(
            resolve_email_workspace_id(
                fallback_workspace_id="workspace_axon_watch",
                workspace_hints=["DashPro"],
            ),
            "workspace_dashpro",
        )
        self.assertEqual(
            resolve_email_workspace_id(
                fallback_workspace_id="workspace_axon_watch",
                workspace_hints=["Unknown"],
                workspace_hint_map={"Unknown": "workspace_custom"},
            ),
            "workspace_custom",
        )

    def test_messages_from_live_bridge_parses_fixture_without_network(self) -> None:
        from io import BytesIO

        email_signal = self.email_signal
        fixture = Path(__file__).resolve().parents[0] / "fixtures" / "email-bridge-analysis.json"
        payload = fixture.read_bytes()

        class _Response:
            def __enter__(self):
                return BytesIO(payload)

            def __exit__(self, exc_type, exc, tb):
                return False

        with patch.object(email_signal, "_email_bridge_enabled", return_value=True), patch.object(
            email_signal,
            "_axon_local_base_url",
            return_value="http://127.0.0.1:7734",
        ), patch.object(email_signal, "urlopen", return_value=_Response()):
            messages = email_signal._messages_from_live_bridge()

        self.assertIsNotNone(messages)
        assert messages is not None
        self.assertEqual(1, len(messages))
        self.assertEqual("<bridge-urgent@example.com>", messages[0]["message_id"])
        self.assertIn("investigate the failing deploy", messages[0]["text"].lower())

        with patch.object(email_signal, "_email_bridge_enabled", return_value=True), patch.object(
            email_signal,
            "_axon_local_base_url",
            return_value="http://127.0.0.1:7734",
        ), patch.object(email_signal, "urlopen", return_value=_Response()), patch.object(
            email_signal,
            "_load_stub_config",
            return_value={
                "enabled": True,
                "workspace_id": "workspace_axon_watch",
                "workspace_names": ["DashPro"],
                "messages": [],
            },
        ):
            items = email_signal.email_inbox_items()

        self.assertEqual(1, len(items))
        self.assertEqual("email", items[0]["source"])
        self.assertEqual("workspace_dashpro", items[0]["workspace_id"])


if __name__ == "__main__":
    unittest.main()
