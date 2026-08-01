"""Mission Control CEO — ask Leads + rank awaiting Lead plans."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_ROOT))

from app.operator_fleet_advice import build_fleet_coach_line  # noqa: E402
from app.operator_mission_control_ceo import (  # noqa: E402
    build_mission_control_critical_work,
    collect_awaiting_lead_plan_facts,
)


class MissionControlCeoTests(unittest.TestCase):
    def test_collects_one_fact_per_workspace(self) -> None:
        plans = [
            {
                "plan_id": "p1",
                "workspace_id": "workspace_dashpro",
                "goal": "Ship parent fees",
            },
            {
                "plan_id": "p2",
                "workspace_id": "workspace_dashpro",
                "goal": "Duplicate twin",
            },
            {
                "plan_id": "p3",
                "workspace_id": "workspace_axon_watch",
                "goal": "Fast Gate repair",
            },
        ]
        leads = [
            {
                "workspace_id": "workspace_dashpro",
                "lead_name": "Dana",
                "display_name": "DashPro",
            },
            {
                "workspace_id": "workspace_axon_watch",
                "lead_name": "Mira",
                "display_name": "Axon-X",
            },
        ]
        with (
            patch(
                "app.workspace_agents.lead_vaxon_handoff.list_awaiting_engagement_plans",
                return_value=plans,
            ),
            patch(
                "app.workspace_agents.fleet_leads_context.collect_fleet_lead_rows",
                return_value=leads,
            ),
        ):
            facts = collect_awaiting_lead_plan_facts()
        self.assertEqual(len(facts), 2)
        self.assertEqual(facts[0]["workspace_id"], "workspace_dashpro")
        self.assertEqual(facts[0]["lead_name"], "Dana")
        self.assertEqual(facts[0]["kind"], "awaiting_lead_plan")

    def test_critical_work_pack_advise(self) -> None:
        plans = [
            {
                "plan_id": "p1",
                "workspace_id": "workspace_dashpro",
                "goal": "Ship parent fees",
            },
        ]
        leads = [
            {
                "workspace_id": "workspace_dashpro",
                "lead_name": "Dana",
                "display_name": "DashPro",
                "owns": "priorities",
            },
        ]
        with (
            patch(
                "app.workspace_agents.lead_vaxon_handoff.list_awaiting_engagement_plans",
                return_value=plans,
            ),
            patch(
                "app.workspace_agents.fleet_leads_context.collect_fleet_lead_rows",
                return_value=leads,
            ),
        ):
            pack = build_mission_control_critical_work(
                focused_workspace_id="workspace_axon_watch",
            )
        self.assertTrue(pack["ok"])
        self.assertEqual(pack["awaiting_plan_count"], 1)
        self.assertIn("Dana", pack["advise"])
        self.assertEqual(pack["winner"]["plan_id"], "p1")

    def test_coach_line_for_awaiting_lead_plan(self) -> None:
        line = build_fleet_coach_line(
            {
                "kind": "awaiting_lead_plan",
                "workspace_id": "workspace_dashpro",
                "display_name": "DashPro",
                "lead_name": "Dana",
                "title": "Ship parent fees",
            },
            focused_workspace_id="workspace_axon_watch",
        )
        self.assertIn("Dana", line)
        self.assertIn("engage", line.lower())


if __name__ == "__main__":
    unittest.main()
