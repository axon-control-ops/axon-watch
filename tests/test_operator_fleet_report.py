from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))


class OperatorFleetReportTests(unittest.TestCase):
    def test_names_active_workspaces_and_verified_leads(self) -> None:
        from app.kairo.operator_deterministic_report import compose_operator_report

        snapshot = {
            "workspace_id": "workspace_axon_watch",
            "briefing": {"advise": "Keep watching", "degraded": {"active": False}},
            "fleet": {"count": 3, "critical_count": 0, "attention_count": 2},
            "roster": {"busy": [], "completed": [], "failed": [], "employees": []},
            "handoffs": [],
            "workspace_reports": [
                self._workspace(
                    workspace_id="workspace_dashpro",
                    display_name="DashPro",
                    roster={
                        "busy": [{"name": "Priya", "role_label": "Frontend"}],
                        "completed": [],
                        "failed": [],
                        "employees": [{"name": "Dana", "role": "lead", "primary": True}],
                    },
                    handoff={
                        "receipt_id": "dash-receipt",
                        "lead_name": "Dana",
                        "headline": "The dashboard fix is verified",
                        "lead_next": "Run the mobile smoke test",
                    },
                ),
                self._workspace(
                    workspace_id="workspace_axon_watch",
                    display_name="Axon Watch",
                    roster={
                        "busy": [],
                        "completed": [{"name": "Reed", "role_label": "Backend"}],
                        "failed": [],
                        "employees": [{"name": "Mira", "role": "lead", "primary": True}],
                    },
                    handoff={
                        "receipt_id": "watch-receipt",
                        "lead_name": "Mira",
                        "headline": "The reporting lane is ready for review",
                        "lead_next": "Run focused tests",
                    },
                    active_runs=0,
                    review_ready_count=1,
                ),
            ],
            "top_signals": [],
            "active_runs": [],
            "pending_approvals": 0,
            "awaiting_engagement_count": 0,
            "next_safe_actions": [],
            "fingerprint": "fleet-report",
        }

        composed = compose_operator_report(snapshot)
        text = composed["text"]
        self.assertIn("Workspaces checked: three", text)
        self.assertIn("DashPro — busy: Priya (Frontend)", text)
        self.assertIn("Axon Watch — recently completed: Reed (Backend)", text)
        self.assertIn("DashPro — Dana: The dashboard fix is verified", text)
        self.assertIn("Axon Watch — Mira: The reporting lane is ready", text)
        self.assertIn("\n\nLead rollups:\n- ", text)
        self.assertNotEqual(text, composed["spoken"])

    @staticmethod
    def _workspace(
        *,
        workspace_id: str,
        display_name: str,
        roster: dict[str, object],
        handoff: dict[str, str],
        active_runs: int = 1,
        review_ready_count: int = 0,
    ) -> dict[str, object]:
        return {
            "workspace_id": workspace_id,
            "display_name": display_name,
            "health": "attention",
            "active_runs": active_runs,
            "review_ready_count": review_ready_count,
            "pending_approvals_count": 0,
            "top_signal_title": "",
            "roster": roster,
            "handoffs": [handoff],
        }


if __name__ == "__main__":
    unittest.main()
