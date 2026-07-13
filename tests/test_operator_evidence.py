from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.operator_evidence import build_operator_evidence  # noqa: E402


class OperatorEvidenceTests(unittest.TestCase):
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
            "app.operator_evidence.list_active_runs",
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

    def test_unsupported_node_raises(self) -> None:
        with self.assertRaises(ValueError):
            build_operator_evidence("unknown_node")


if __name__ == "__main__":
    unittest.main()
