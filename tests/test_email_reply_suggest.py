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
        self.assertIn("requested update", draft["reply_body"].lower())
        self.assertEqual("capture_follow_up", draft["recommended_action"])

    def test_reply_to_sender_request_ignores_quoted_history(self) -> None:
        draft = suggest_email_reply(
            subject=(
                "Re: RFQ26052 — Quotation Submission: MNT240XED Magnetic Name Tags "
                "(9 000 units) — THAPELOSEGO"
            ),
            sender='"Visser, Mathilda" <Visser.Ma@dbe.gov.za>',
            text=(
                "Good day,\n\n"
                "Kindly provide us with the batch number for the product quoted, namely "
                "the MNT240XED Magnetic Name Tag, in order for us to verify that it is the exact item.\n\n"
                "________________________________\n"
                "From: info@thapelosego.co.za <info@thapelosego.co.za>\n"
                "Sent: Thursday, 20 August\n"
                "Please note that a batch number is a unique identification code.\n"
                "Please send it to both my emails addresses as listed below "
                "Visser.Ma@dbe.gov.za VisserMathilda.dbe@hotmail.com\n"
            ),
        )
        body = draft["reply_body"]
        self.assertTrue(body.startswith("Hi Mathilda,"))
        self.assertIn("MNT240XED Magnetic Name Tag", body)
        self.assertIn("batch number", body)
        self.assertNotIn("Please note that a batch number", body)
        self.assertNotIn("Please send it to both my emails", body)
        self.assertNotIn("Timing noted", body)
        self.assertNotIn("Axon operator", body)
        self.assertTrue(body.rstrip().endswith("Kind regards,"))

    def test_real_operator_name_is_used_as_signature(self) -> None:
        draft = suggest_email_reply(
            subject="Please send the batch number",
            sender="Mathilda Visser <visser@example.com>",
            text="Please send the batch number.",
            operator_name="Thapelo Sego",
        )
        self.assertIn("\nKind regards,\nThapelo Sego\n", draft["reply_body"])


if __name__ == "__main__":
    unittest.main()
