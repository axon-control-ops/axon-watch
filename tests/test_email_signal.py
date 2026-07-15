"""Email triage signal emission tests."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

WATCH_ROOT = Path(__file__).resolve().parents[1] / "services" / "axon-watch"
sys.path.insert(0, str(WATCH_ROOT))

from app.signals.email_signal import email_inbox_item, email_inbox_items  # noqa: E402
from app.signals.email_triage import analyze_email_message  # noqa: E402


class EmailTriageTests(unittest.TestCase):
    def test_analyze_email_message_extracts_actions_risks_and_commitments(self) -> None:
        analysis = analyze_email_message(
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
        self.assertTrue(analysis["action_requests"])
        self.assertTrue(analysis["risks"])
        self.assertTrue(analysis["commitments"])
        self.assertIn("DashPro", analysis["workspace_hints"])

    def test_email_inbox_item_requires_priority_threshold(self) -> None:
        low = analyze_email_message(
            {
                "subject": "Weekly digest",
                "text": "Here is this week's reading list.",
                "from": "Newsletter <news@example.com>",
                "message_id": "<low@example.com>",
            }
        )
        self.assertIsNone(email_inbox_item(low, workspace_id="workspace_axon_watch"))

        high = analyze_email_message(
            {
                "subject": "Urgent: DashPro deploy failed",
                "text": "Please investigate the failing deploy today. We cannot ship.",
                "from": "CTO <cto@example.com>",
                "message_id": "<high@example.com>",
            },
            workspace_names=["DashPro"],
        )
        item = email_inbox_item(high, workspace_id="workspace_axon_watch")
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
                "app.signals.email_imap_poll.fetch_native_email_messages",
                return_value=None,
            ), patch("app.signals.email_signal._messages_from_live_bridge", return_value=None):
                items = email_inbox_items(stub_path=path)
        self.assertEqual(1, len(items))
        self.assertTrue(str(items[0]["signal_id"]).startswith("signal_email_"))
        self.assertEqual(items[0]["workspace_id"], "workspace_dashpro")
        self.assertIn("suggested_reply_body", items[0]["meta"])

    def test_email_inbox_items_prefers_native_imap(self) -> None:
        with patch(
            "app.signals.email_imap_poll.fetch_native_email_messages",
            return_value=[
                {
                    "message_id": "<native@example.com>",
                    "from": "Ops <ops@example.com>",
                    "subject": "Urgent: please fix DashPro today",
                    "text": "We cannot ship until this is fixed.",
                    "snippet": "We cannot ship until this is fixed.",
                }
            ],
        ), patch("app.signals.email_signal._messages_from_live_bridge", return_value=None):
            items = email_inbox_items()
        self.assertEqual(1, len(items))
        self.assertIn("suggested_reply_subject", items[0]["meta"])
        self.assertTrue(str(items[0]["meta"]["suggested_reply_subject"]).startswith("Re:"))

    def test_resolve_email_workspace_id_from_hints(self) -> None:
        from app.signals.email_signal import resolve_email_workspace_id

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
        from app.signals import email_signal
        from io import BytesIO

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
