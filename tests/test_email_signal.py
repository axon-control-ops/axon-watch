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
            with patch("app.signals.email_signal._messages_from_live_bridge", return_value=None):
                items = email_inbox_items(stub_path=path)
        self.assertEqual(1, len(items))
        self.assertTrue(str(items[0]["signal_id"]).startswith("signal_email_"))
        self.assertEqual(items[0]["workspace_id"], "workspace_dashpro")

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


if __name__ == "__main__":
    unittest.main()
