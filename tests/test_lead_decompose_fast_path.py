from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.chat.lane_b_lead_decompose_fast_path import (  # noqa: E402
    maybe_post_lead_decompose_message,
)
from app.workspace_agents.lead_task_plan import LeadPlanRosterMember, LeadTaskPlan, LeadTaskPlanItem  # noqa: E402


ROSTER = [
    LeadPlanRosterMember(role="lead", name="Dana", owns="priorities"),
    LeadPlanRosterMember(role="frontend", name="Priya", owns="UI and Expo"),
    LeadPlanRosterMember(role="backend", name="Marco", owns="APIs and persistence"),
    LeadPlanRosterMember(role="integrations", name="Soren", owns="CI"),
    LeadPlanRosterMember(role="watcher", name="Cass", owns="signals"),
]


class LeadDecomposeFastPathTests(unittest.TestCase):
    def test_materializes_multi_domain_ask(self) -> None:
        saved: list[dict] = []

        def save_message(payload: dict) -> dict:
            saved.append(payload)
            return payload

        preview = LeadTaskPlan(
            goal="Fix the quality-gate API failure and the enrollment confirmation popup",
            mode="decompose",
            items=[
                LeadTaskPlanItem(
                    plan_key="plan-01-frontend",
                    goal="Frontend: UI aspects",
                    owner_role="frontend",
                ),
                LeadTaskPlanItem(
                    plan_key="plan-02-backend",
                    goal="Backend: API aspects",
                    owner_role="backend",
                ),
            ],
            ordered_keys=["plan-01-frontend", "plan-02-backend"],
        )
        materialize = {
            "plan_id": "plan_test",
            "mode": "decompose",
            "tasks": [
                {"owner_role": "frontend", "goal": "Frontend: UI aspects"},
                {"owner_role": "backend", "goal": "Backend: API aspects"},
            ],
            "runs": [{"run_id": "run_1", "owner_role": "frontend"}],
            "deferred": [],
        }

        handoff = {
            "run_id": "run_lead_handoff",
            "phase": "completed",
            "employee_role": "lead",
        }
        with (
            patch(
                "app.chat.lane_b_lead_decompose_fast_path._roster_members",
                return_value=ROSTER,
            ),
            patch(
                "app.chat.lane_b_lead_decompose_fast_path.resolve_lead_task_plan",
                return_value=preview,
            ),
            patch(
                "app.chat.lane_b_lead_decompose_fast_path.materialize_lead_fan_out",
                return_value=materialize,
            ),
            patch(
                "app.chat.lane_b_lead_decompose_fast_path.record_lead_handoff_run",
                return_value=handoff,
            ),
            patch(
                "app.chat.lane_b_lead_decompose_fast_path._kick_continuous_dispatch",
            ),
        ):
            response = maybe_post_lead_decompose_message(
                workspace_id="workspace_dashpro",
                content="Fix the quality-gate API failure and the enrollment confirmation popup",
                thread_id="thread_lead",
                employee_role="lead",
                lead_name="Dana",
                composer_mode="agent",
                created_at="2026-07-29T12:00:00Z",
                save_message=save_message,
                new_message_id=lambda prefix: f"{prefix}_1",
                bind_attachments=lambda _mid: [],
            )

        self.assertIsNotNone(response)
        assert response is not None
        self.assertEqual("run_lead_handoff", response["run_id"])
        self.assertEqual("completed", response["run"]["phase"])
        self.assertFalse(response["streaming"])
        self.assertEqual("plan_test", response["lead_decompose"]["plan_id"])
        agent = next(row for row in saved if row["role"] == "agent")
        self.assertIn("decomposed the work", agent["content"])
        self.assertIn("frontend:", agent["content"].lower())
        self.assertIn("Fleet:", agent["content"])
        self.assertIn("Confidence: 8/10", agent["content"])
        self.assertEqual("run_lead_handoff", agent["run_id"])

    def test_skips_assign_all_intent(self) -> None:
        response = maybe_post_lead_decompose_message(
            workspace_id="workspace_dashpro",
            content="assign all agents to start working on Gate 5",
            thread_id="thread_lead",
            employee_role="lead",
            lead_name="Dana",
            composer_mode="agent",
            created_at="2026-07-29T12:00:00Z",
            save_message=lambda payload: payload,
            new_message_id=lambda prefix: f"{prefix}_1",
            bind_attachments=lambda _mid: [],
        )
        self.assertIsNone(response)


if __name__ == "__main__":
    unittest.main()
