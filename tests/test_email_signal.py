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

    def test_analyze_email_message_suppresses_duplicate_ci_mail(self) -> None:
        analysis = self.analyze_email_message(
            {
                "subject": "[axon-control-ops/axon-watch] Run failed: Axon-X Fast Gate",
                "text": "GitHub Actions workflow run failed. View results.",
                "from": "axon-control-ops <notifications@github.com>",
                "message_id": "<ci-mail@example.com>",
            }
        )
        self.assertTrue(analysis["automated_dev_notification"])
        self.assertLessEqual(analysis["priority"], 40)
        self.assertEqual(analysis["recommended_action"], "monitor_engineering_signal")
        self.assertIsNone(self.email_inbox_item(analysis, workspace_id="workspace_axon_watch"))

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

    def test_email_inbox_items_scope_signal_ids_by_mailbox(self) -> None:
        with patch(
            "app.signals.email_signal.fetch_native_email_messages",
            return_value=[
                {
                    "message_id": "<shared-message@example.com>",
                    "account_id": "acct-ops",
                    "account_email": "ops@example.com",
                    "from": "Client <client@example.com>",
                    "subject": "Urgent: please confirm today",
                    "text": "Please confirm this today. We cannot wait.",
                    "snippet": "Please confirm this today. We cannot wait.",
                },
                {
                    "message_id": "<shared-message@example.com>",
                    "account_id": "acct-sales",
                    "account_email": "sales@example.com",
                    "from": "Client <client@example.com>",
                    "subject": "Urgent: please confirm today",
                    "text": "Please confirm this today. We cannot wait.",
                    "snippet": "Please confirm this today. We cannot wait.",
                },
            ],
        ), patch("app.signals.email_signal._messages_from_live_bridge", return_value=None):
            items = self.email_inbox_items()

        self.assertEqual(2, len(items))
        signal_ids = {str(item["signal_id"]) for item in items}
        self.assertEqual(2, len(signal_ids))
        self.assertTrue(any("acct-ops" in signal_id for signal_id in signal_ids))
        self.assertTrue(any("acct-sales" in signal_id for signal_id in signal_ids))

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

    def test_messages_from_live_bridge_is_retired(self) -> None:
        email_signal = self.email_signal

        with patch.object(email_signal, "_email_bridge_enabled", return_value=True):
            messages = email_signal._messages_from_live_bridge()

        self.assertIsNone(messages)

        with patch.object(email_signal, "_email_bridge_enabled", return_value=True), patch.object(
            email_signal,
            "_load_stub_config",
            return_value={
                "enabled": True,
                "workspace_id": "workspace_axon_watch",
                "workspace_names": ["DashPro"],
                "messages": [
                    {
                        "message_id": "<stub-dashpro@example.com>",
                        "from": "CTO <cto@example.com>",
                        "subject": "Urgent: DashPro deploy failed",
                        "text": "Please investigate the failing deploy today.",
                        "snippet": "Please investigate the failing deploy today.",
                    }
                ],
            },
        ):
            items = email_signal.email_inbox_items()

        self.assertEqual(1, len(items))
        self.assertEqual("email", items[0]["source"])
        self.assertEqual("workspace_dashpro", items[0]["workspace_id"])


class NoReplySenderTests(unittest.TestCase):
    """Regression guard: a no-reply address must never get a drafted reply.

    A GitHub "[ACTION REQUIRED] ... will soon require 2FA" account notice from
    noreply@github.com was drafted a full reply addressed to GitHub as if it
    were a person -- the sender-shape check existed but was only ever
    consulted inside the narrow billing/dev-notification helpers, not as a
    general rule.
    """

    def setUp(self) -> None:
        _watch_app, self._saved_modules = load_watch_app()
        from app.signals import email_signal as email_signal_module  # noqa: WPS433
        from app.signals.email_triage import analyze_email_message, is_no_reply_sender  # noqa: WPS433

        self.email_signal = email_signal_module
        self.analyze_email_message = analyze_email_message
        self.is_no_reply_sender = is_no_reply_sender

    def tearDown(self) -> None:
        restore_app_modules(self._saved_modules)

    def test_github_account_notice_is_recognised_as_no_reply(self) -> None:
        # The exact failing case: an action-required security notice with none
        # of the billing or CI/deploy body markers, from a plain noreply sender.
        analysis = self.analyze_email_message(
            {
                "subject": "[ACTION REQUIRED] Your GitHub account, axon-control-ops, will soon require 2FA",
                "from": "GitHub <noreply@github.com>",
                "text": (
                    "We're reaching out to let you know that, as announced last "
                    "year, we have officially begun requiring users who "
                    "contribute code to enable two-factor authentication."
                ),
                "message_id": "<gh-2fa@github.com>",
            }
        )
        self.assertTrue(analysis["no_reply_sender"])
        self.assertEqual(analysis["recommended_action"], "monitor_email")
        self.assertIn("no-reply", analysis["recommended_detail"].lower())

    def test_no_reply_signal_carries_no_reply_draft(self) -> None:
        analysis = self.analyze_email_message(
            {
                "subject": "[ACTION REQUIRED] Your GitHub account, axon-control-ops, will soon require 2FA",
                "from": "GitHub <noreply@github.com>",
                "text": "Please enable two-factor authentication on your account.",
                "message_id": "<gh-2fa-2@example.com>",
            }
        )
        # Below the signal priority threshold entirely -- the same treatment
        # already given to promotional/billing automated mail in this file.
        item = self.email_signal.email_inbox_item(analysis, workspace_id="workspace_axon_watch")
        self.assertIsNone(item)

    def test_ordinary_sender_with_action_language_still_gets_a_draft(self) -> None:
        # The fix must not suppress replies generally -- only for addresses
        # that cannot receive one.
        analysis = self.analyze_email_message(
            {
                "subject": "Please confirm the deploy window",
                "from": "Ops Lead <ops@example.com>",
                "text": "Could you confirm the deploy window for tomorrow?",
                "message_id": "<ops-1@example.com>",
            }
        )
        self.assertFalse(analysis["no_reply_sender"])
        self.assertEqual(analysis["recommended_action"], "capture_follow_up")
        item = self.email_signal.email_inbox_item(analysis, workspace_id="workspace_axon_watch")
        self.assertIsNotNone(item)
        self.assertTrue(item["meta"]["suggested_reply_body"])

    def test_suggested_reply_matches_the_full_text_classification_past_280_chars(self) -> None:
        # Regression: email_inbox_item used to hand suggest_email_reply the
        # already-truncated 280-char analysis["snippet"] (not the original
        # body), which re-ran analyze_email_message a second time on that
        # shorter text and could reach a *different* recommended_action than
        # the one already computed from the full email -- silently
        # overriding it in meta, and quoting a sentence fragment truncated
        # mid-word. This body's actionable request starts well past the
        # 280-char mark, so the bug reliably reproduces here.
        padding = "Good day, I hope this email finds you well. " * 6
        text = (
            f"{padding}"
            "Please send us the batch number for the product quoted "
            "so we can confirm it is the exact item requested by Friday."
        )
        self.assertGreater(len(text), 280)
        analysis = self.analyze_email_message(
            {
                "subject": "Re: Quotation follow-up",
                "from": '"Visser, Mathilda" <visser@example.gov>',
                "text": text,
                "message_id": "<visser-1@example.gov>",
            }
        )
        self.assertEqual(analysis["recommended_action"], "capture_follow_up")
        item = self.email_signal.email_inbox_item(analysis, workspace_id="workspace_tps")
        self.assertIsNotNone(item)
        # The bug's symptom: meta ends up "monitor_email" (or a reply quoting
        # a mid-word fragment) despite the full-text analysis above already
        # correctly reaching "capture_follow_up".
        self.assertEqual(item["meta"]["recommended_action"], "capture_follow_up")
        self.assertIn("batch number", item["meta"]["suggested_reply_body"])
        self.assertTrue(item["meta"]["suggested_reply_body"].startswith("Hi Mathilda,"))
        self.assertNotIn("Axon operator", item["meta"]["suggested_reply_body"])

    def test_suggested_reply_for_batch_number_is_sender_facing(self) -> None:
        text = (
            "Good day,\n\n"
            "Kindly provide us with the batch number for the product quoted, namely "
            "the MNT240XED Magnetic Name Tag, in order for us to verify that it is the exact item.\n\n"
            "________________________________\n"
            "From: info@thapelosego.co.za <info@thapelosego.co.za>\n"
            "Sent: Thursday, 20 August\n"
            "Please note that a batch number is a unique identification code.\n"
            "Please send it to both my emails addresses as listed below "
            "Visser.Ma@dbe.gov.za VisserMathilda.dbe@hotmail.com\n"
        )
        analysis = self.analyze_email_message(
            {
                "subject": (
                    "Re: RFQ26052 — Quotation Submission: MNT240XED Magnetic Name Tags "
                    "(9 000 units) — THAPELOSEGO"
                ),
                "from": '"Visser, Mathilda" <Visser.Ma@dbe.gov.za>',
                "text": text,
                "message_id": "<visser-batch@example.gov>",
            }
        )
        item = self.email_signal.email_inbox_item(analysis, workspace_id="workspace_tps")
        self.assertIsNotNone(item)
        body = item["meta"]["suggested_reply_body"]
        self.assertTrue(body.startswith("Hi Mathilda,"))
        self.assertIn("MNT240XED Magnetic Name Tag", body)
        self.assertIn("batch number", body)
        self.assertNotIn("Please note that a batch number", body)
        self.assertNotIn("Please send it to both my emails", body)
        self.assertNotIn("Timing noted", body)
        self.assertNotIn("Axon operator", body)

    def test_action_extraction_ignores_quoted_history_and_disclaimer_footers(self) -> None:
        # Regression: a real government-sender email whose own IT disclaimer
        # footer ("Please be advised that... email servers are currently
        # experiencing technical difficulties") contains the word "please"
        # like any real request does. Before this fix, that boilerplate line
        # was picked up as an action_request/due_marker ahead of the sender's
        # actual ask, so the drafted reply answered the disclaimer instead of
        # the real message -- and a quoted "Sent: Thursday, 20 August" header
        # from a forwarded thread was read as a due date the sender gave us.
        text = (
            "Good Day, "
            "Following a comprehensive evaluation process, we are pleased to advise that your "
            "quotation has been accepted. Please proceed with delivery of the 9 000 units by 2026-08-28. "
            "________________________________ "
            "IMPORTANT NOTICE - EMAIL COMMUNICATION Please be advised that the Department's official "
            "email servers are currently experiencing technical difficulties."
        )
        analysis = self.analyze_email_message(
            {
                "subject": "RE: Official appointment / order confirmation",
                "from": '"Visser, Mathilda" <visser@example.gov>',
                "text": text,
                "message_id": "<visser-2@example.gov>",
            }
        )
        self.assertEqual(analysis["recommended_action"], "capture_follow_up")
        self.assertEqual(len(analysis["action_requests"]), 1)
        self.assertIn("proceed with delivery", analysis["action_requests"][0])
        self.assertNotIn("technical difficulties", " ".join(analysis["action_requests"]))
        self.assertEqual(analysis["due_markers"], ["2026-08-28"])

    def test_action_extraction_drops_all_caps_section_headers(self) -> None:
        # Regression: a standalone ALL-CAPS section header ("REQUIRED
        # DOCUMENTATION") sits on its own line in the source email, but
        # whitespace-collapsing (needed to find sentences at all) erases
        # that line break, gluing the header onto the next real sentence --
        # so the extracted action request read "REQUIRED DOCUMENTATION
        # Furthermore, kindly ensure..." instead of just the sentence.
        text = (
            "Good day,\n\n"
            "DELIVERY SCHEDULE\n\n"
            "You are kindly requested to confirm your delivery schedule for Monday.\n\n"
            "REQUIRED DOCUMENTATION\n\n"
            "Furthermore, kindly ensure that the attached form is signed and returned."
        )
        analysis = self.analyze_email_message(
            {
                "subject": "Order confirmation",
                "from": '"Visser, Mathilda" <visser@example.gov>',
                "text": text,
                "message_id": "<visser-3@example.gov>",
            }
        )
        joined = " ".join(analysis["action_requests"])
        self.assertNotIn("DELIVERY SCHEDULE", joined)
        self.assertNotIn("REQUIRED DOCUMENTATION", joined)
        self.assertIn("Furthermore, kindly ensure", joined)

    def test_is_no_reply_sender_matches_common_shapes(self) -> None:
        for sender in (
            "GitHub <noreply@github.com>",
            "Billing <no-reply@stripe.com>",
            "Mailer Daemon <mailer-daemon@example.com>",
            "Postmaster <postmaster@example.com>",
        ):
            with self.subTest(sender=sender):
                self.assertTrue(self.is_no_reply_sender(sender))
        self.assertFalse(self.is_no_reply_sender("Ops Lead <ops@example.com>"))

    def test_no_reply_billing_notice_is_not_double_classified(self) -> None:
        # A no-reply billing notice must still take the billing branch, not the
        # generic no-reply one -- both suppress the reply, but the detail text
        # should stay specific to what the email actually is.
        analysis = self.analyze_email_message(
            {
                "subject": "Your invoice is ready",
                "from": "Billing <billing-noreply@vendor.com>",
                "text": "Your invoice is ready. Amount due: $42.00. Disregard this email if already paid.",
                "message_id": "<inv-1@example.com>",
            }
        )
        self.assertTrue(analysis["automated_billing"])
        self.assertIn("billing", analysis["recommended_detail"].lower())


if __name__ == "__main__":
    unittest.main()
