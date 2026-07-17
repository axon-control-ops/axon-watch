from __future__ import annotations

import sys
import unittest
from typing import Any, Callable
from unittest.mock import patch

from tests.support.control_plane_app_loader import prepare_control_plane_imports

build_operator_evidence: Callable[[str], dict[str, Any]]


class OperatorEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self._saved_modules = prepare_control_plane_imports()
        self.addCleanup(self._restore_control_plane_modules)

        global build_operator_evidence
        from app.operator_evidence import build_operator_evidence as _build_operator_evidence

        build_operator_evidence = _build_operator_evidence

    def _restore_control_plane_modules(self) -> None:
        for name in list(sys.modules):
            if name == "app" or name.startswith("app."):
                del sys.modules[name]
        sys.modules.update(self._saved_modules)

    def test_workspace_evidence_includes_open_ide_action(self) -> None:
        with patch(
            "app.operator_evidence.get_workspace_record",
            return_value={
                "workspace_id": "workspace_dashpro",
                "display_name": "DashPro",
                "connection_kind": "child_project",
            },
        ), patch(
            "app.operator_evidence.build_inbox_response",
            return_value={"items": [], "count": 0},
        ), patch(
            "app.operator_evidence.list_operator_facing_active_runs",
            return_value=[],
        ):
            payload = build_operator_evidence("ws_workspace_dashpro")

        self.assertEqual("workspace", payload["kind"])
        self.assertEqual("DashPro", payload["title"])
        self.assertTrue(
            any(action.get("target") == "workspace" for action in payload["actions"])
        )

    def test_signal_evidence_surfaces_sentry_sample_and_handoff(self) -> None:
        with patch(
            "app.operator_evidence.build_inbox_response",
            return_value={
                "items": [
                    {
                        "signal_id": "signal_monitor_dashpro_sentry_critical",
                        "workspace_id": "workspace_dashpro",
                        "title": "DashPro Sentry critical",
                        "summary": "Unresolved issues rising",
                        "severity": "critical",
                        "status": "open",
                        "source": "watch",
                        "action_type": "investigate",
                        "delivery_state": "pending",
                        "meta": {
                            "signal_family": "child_project_monitor",
                            "check_id": "dashpro_sentry",
                            "monitor_status": "critical",
                            "sentry_issues": [
                                {
                                    "id": "123",
                                    "title": "TypeError in payments",
                                    "count": 12,
                                    "permalink": "https://sentry.io/issues/123/",
                                }
                            ],
                        },
                    }
                ],
                "count": 1,
            },
        ):
            payload = build_operator_evidence(
                "sig_signal_monitor_dashpro_sentry_critical"
            )

        self.assertEqual("signal", payload["kind"])
        fact_labels = {fact["label"] for fact in payload["facts"]}
        self.assertIn("Monitor check", fact_labels)
        self.assertIn("Family", fact_labels)
        self.assertTrue(
            any(action.get("target") == "handoff" for action in payload["actions"])
        )
        self.assertEqual("Sentry issues", payload["sections"][0]["title"])
        self.assertIn("sentry.io", payload["sections"][0]["items"][0]["detail"])

    def test_signal_evidence_surfaces_email_triage_sections(self) -> None:
        with patch(
            "app.operator_evidence.build_inbox_response",
            return_value={
                "items": [
                    {
                        "signal_id": "signal_email_stub_urgent",
                        "workspace_id": "workspace_axon_watch",
                        "title": "Email needs follow-up: Urgent: DashPro deploy failed",
                        "summary": "CTO — Respond to the blocker.",
                        "severity": "high",
                        "status": "open",
                        "source": "email",
                        "action_type": "investigate",
                        "delivery_state": "pending",
                        "meta": {
                            "signal_family": "email_triage",
                            "sender": "CTO <cto@example.com>",
                            "subject": "Urgent: DashPro deploy failed",
                            "snippet": "Please investigate the failing deploy today.",
                            "recommended_action": "reply_or_investigate",
                            "recommended_detail": "Respond to the blocker.",
                            "risks": ["We cannot ship until this is fixed."],
                            "action_requests": ["Please investigate the failing deploy today."],
                        },
                    }
                ],
                "count": 1,
            },
        ):
            payload = build_operator_evidence("sig_signal_email_stub_urgent")

        fact_labels = {fact["label"] for fact in payload["facts"]}
        self.assertIn("Sender", fact_labels)
        self.assertIn("Subject", fact_labels)
        self.assertIn("Recommended action", fact_labels)
        section_titles = [section["title"] for section in payload["sections"]]
        self.assertIn("Email", section_titles)
        self.assertIn("Risks", section_titles)
        self.assertIn("Action requests", section_titles)

    def test_unsupported_node_raises(self) -> None:
        with self.assertRaises(ValueError):
            build_operator_evidence("unknown_node")


if __name__ == "__main__":
    unittest.main()
