"""Deterministic REPORT lane — roster + verified Lead handoffs."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.support.control_plane_app_loader import prepare_control_plane_imports
from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))


_MOCK_BRIEFING = {
    "scope": {"workspace_id": "workspace_dashpro", "display_name": "DashPro"},
    "notice": "",
    "advise": "I'd check Priya's Lead next before starting more UI",
    "pending_approvals": {"count": 0},
    "top_signals": [],
    "active_runs": [],
    "next_safe_actions": [],
    "awaiting_engagement_count": 0,
    "degraded": {"active": False},
    "connectivity": {"watch_connected": True},
    "cli_runtime": {"dispatch_ready": True, "blockers": []},
}

_MOCK_FLEET = {
    "items": [
        {"workspace_id": "ws_a", "tone": "nominal"},
        {"workspace_id": "ws_b", "tone": "nominal"},
    ]
}
_MOCK_GRAPH = {"nodes": [], "edges": []}

_BRIEFING_PATCH = "app.kairo.conversation_context_pack.build_operator_briefing"
_FLEET_PATCH = "app.kairo.conversation_context_pack.build_operator_fleet_health"
_GRAPH_PATCH = "app.kairo.conversation_context_pack.build_operator_brain_graph"


class OperatorDeterministicReportTests(unittest.TestCase):
    def setUp(self) -> None:
        self._saved = prepare_control_plane_imports()
        self.addCleanup(self._restore)
        from app.persistence import chat_store, run_store, task_store
        from app.workspace_agents import lead_adhoc_receipt_store, lead_plan_store

        isolate_control_plane_db(self, run_store)
        task_store.reset_store()
        lead_plan_store.reset_store()
        lead_adhoc_receipt_store.reset_store()
        chat_store.reset_store()

    def _restore(self) -> None:
        for name in list(sys.modules):
            if name == "app" or name.startswith("app."):
                del sys.modules[name]
        sys.modules.update(self._saved)

    def test_report_intent_detects_hotwords_and_expanded_prompt(self) -> None:
        from app.kairo.operator_deterministic_report import is_operator_report_request

        self.assertTrue(is_operator_report_request("REPORT"))
        self.assertTrue(is_operator_report_request("status"))
        self.assertTrue(is_operator_report_request("where do we stand"))
        self.assertTrue(
            is_operator_report_request(
                "REPORT — give me a JARVIS-style second-brain stand-up in plain English."
            )
        )
        self.assertFalse(is_operator_report_request("any approvals?"))
        self.assertFalse(is_operator_report_request("open DashPro workspace"))

    def test_compose_names_busy_and_completed_and_receipt_handoffs(self) -> None:
        from app.kairo.operator_deterministic_report import (
            compose_operator_report,
        )
        from app.workspace_agents.lead_vaxon_handoff import post_ad_hoc_lead_takeover_to_vaxon

        with patch("app.live_events.broadcast_material_change"):
            posted = post_ad_hoc_lead_takeover_to_vaxon(
                workspace_id="workspace_dashpro",
                run_id="run_priya_done",
                employee_role="frontend",
                employee_name="Priya",
                phase="completed",
                lead_next="decide notify campaign once storage is live",
                lead_summary="Built parent graduation survey card",
                blockers="Marco owns storage/payment migration",
            )
        self.assertEqual("posted", posted.get("status"))

        snapshot = {
            "workspace_id": "workspace_dashpro",
            "briefing": _MOCK_BRIEFING,
            "fleet": _MOCK_FLEET,
            "roster": {
                "workspace_id": "workspace_dashpro",
                "company_name": "DashPro",
                "employees": [],
                "busy": [
                    {
                        "employee_id": "emp_marco",
                        "name": "Marco",
                        "role": "backend",
                        "role_label": "Backend",
                        "status": "executing",
                        "active_run_id": "run_marco_1",
                    }
                ],
                "completed": [
                    {
                        "employee_id": "emp_priya",
                        "name": "Priya",
                        "role": "frontend",
                        "role_label": "Frontend",
                        "status": "idle",
                        "last_outcome": "completed",
                    }
                ],
                "failed": [],
            },
            "handoffs": [
                {
                    "receipt_id": posted.get("receipt_id"),
                    "headline": "Priya (frontend) completed — Built parent graduation survey card",
                    "lead_next": "decide notify campaign once storage is live",
                    "lead_summary": "Built parent graduation survey card",
                }
            ],
            "top_signals": [],
            "active_runs": [],
            "pending_approvals": 0,
            "awaiting_engagement_count": 0,
            "next_safe_actions": [],
            "fingerprint": "abc",
        }
        composed = compose_operator_report(snapshot)
        text = composed["text"]
        self.assertIn("Attention:", text)
        self.assertIn("Work in flight:", text)
        self.assertIn("Marco (Backend) is executing", text)
        self.assertIn("Priya (Frontend) just completed", text)
        self.assertIn("Lead rollups:", text)
        self.assertIn("graduation survey", text.lower())
        self.assertIn("Lead next:", text)
        self.assertNotIn("Confidence:", text)
        self.assertIn("Fleet:", text)
        self.assertIn("Next move:", text)

        # Empty state stays calm.
        empty = compose_operator_report(
            {
                "workspace_id": "workspace_dashpro",
                "briefing": {**_MOCK_BRIEFING, "advise": ""},
                "fleet": _MOCK_FLEET,
                "roster": {
                    "busy": [],
                    "completed": [],
                    "failed": [],
                    "employees": [],
                },
                "handoffs": [],
                "top_signals": [],
                "active_runs": [],
                "pending_approvals": 0,
                "awaiting_engagement_count": 0,
                "next_safe_actions": [],
                "fingerprint": "empty",
            }
        )
        self.assertIn("nothing screaming", empty["text"].lower())
        self.assertIn("idle", empty["text"].lower())

    @patch(_GRAPH_PATCH, return_value=_MOCK_GRAPH)
    @patch(_FLEET_PATCH, return_value=_MOCK_FLEET)
    @patch(_BRIEFING_PATCH, return_value=_MOCK_BRIEFING)
    @patch("app.kairo_conversation.dispatch_ide_composer")
    def test_converse_report_uses_deterministic_lane_not_lane_b(
        self,
        mock_dispatch,
        *_mocks: object,
    ) -> None:
        from app.kairo_conversation import converse_turn

        with patch(
            "app.kairo.operator_deterministic_report._roster_snapshot",
            return_value={
                "workspace_id": "workspace_dashpro",
                "company_name": "DashPro",
                "employees": [],
                "busy": [
                    {
                        "employee_id": "emp_dana",
                        "name": "Dana",
                        "role": "lead",
                        "role_label": "Lead",
                        "status": "executing",
                        "active_run_id": "run_dana_1",
                    }
                ],
                "completed": [],
                "failed": [],
            },
        ):
            payload = converse_turn(
                content="REPORT",
                session_id="report-lane-session",
                workspace_id="workspace_dashpro",
                use_runtime=True,
                answer_tier="fast",
            )
        self.assertEqual("status_question", payload["turn_kind"])
        self.assertEqual("template", payload["source"])
        self.assertEqual("deterministic_report", payload.get("dispatch_lane"))
        reply = str(payload["reply"])
        self.assertIn("Dana", reply)
        # Spoken normalization turns "Attention:" into "Attention,".
        self.assertRegex(reply, r"Attention[,:]")
        self.assertRegex(reply, r"Work in flight[,:]")
        mock_dispatch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
