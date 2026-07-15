"""Email reply suggestion tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
if str(CONTROL_PLANE_ROOT) not in sys.path:
    sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.email_reply_suggest import suggest_email_reply  # noqa: E402


class EmailReplySuggestTests(unittest.TestCase):
    def test_suggest_reply_for_urgent_action(self) -> None:
        draft = suggest_email_reply(
            subject="Urgent: please fix DashPro",
            sender="CTO <cto@example.com>",
            text="We cannot ship until this is fixed today.",
        )
        self.assertTrue(draft["reply_subject"].startswith("Re:"))
        self.assertIn("looking into it", draft["reply_body"].lower())
        self.assertEqual("reply_or_investigate", draft["recommended_action"])
        self.assertEqual("CTO <cto@example.com>", draft["to"])

    def test_suggest_reply_for_follow_up(self) -> None:
        draft = suggest_email_reply(
            subject="Please review the invoice",
            sender="Finance <finance@example.com>",
            text="Can you confirm payment by Friday?",
        )
        self.assertTrue(draft["reply_subject"].startswith("Re:"))
        self.assertIn("follow-up", draft["reply_body"].lower())
        self.assertEqual("capture_follow_up", draft["recommended_action"])


if __name__ == "__main__":
    unittest.main()
