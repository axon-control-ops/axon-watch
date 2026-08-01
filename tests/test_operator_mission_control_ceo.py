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
    engage_awaiting_lead_plans,
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

    def test_critical_work_surfaces_board_when_no_lead_plans(self) -> None:
        plate = {
            "waiting": 3,
            "in_progress": 1,
            "needs_attention": 12,
            "pending_approvals": 0,
            "cross_workspace": 2,
            "total_open_plate": 18,
            "load": "critical",
            "sample_titles": ["VAXON attend: Reed failed"],
            "focused_workspace_id": "workspace_axon_watch",
        }
        with (
            patch(
                "app.workspace_agents.lead_vaxon_handoff.list_awaiting_engagement_plans",
                return_value=[],
            ),
            patch(
                "app.workspace_agents.fleet_leads_context.collect_fleet_lead_rows",
                return_value=[],
            ),
            patch(
                "app.mission_control_plate.collect_mission_control_plate",
                return_value=plate,
            ),
            patch(
                "app.persistence.operator_presence_settings_store.load_settings",
                return_value={"autonomy_mode": "full"},
            ),
        ):
            pack = build_mission_control_critical_work(
                focused_workspace_id="workspace_axon_watch",
            )
        self.assertTrue(pack["ok"])
        self.assertEqual(pack["awaiting_plan_count"], 0)
        self.assertIn("Waiting", pack["advise"])
        self.assertNotEqual(pack["advise"], "")
        self.assertEqual(pack["plate"]["waiting"], 3)

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

    def test_engage_requires_full_autonomy(self) -> None:
        with patch(
            "app.persistence.operator_presence_settings_store.load_settings",
            return_value={"autonomy_mode": "assisted"},
        ):
            result = engage_awaiting_lead_plans(require_full_autonomy=True)
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "autonomy_not_full")
        self.assertEqual(result["engaged"], [])

    def test_engage_completes_one_plan_per_workspace(self) -> None:
        plans = [
            {
                "plan_id": "p1",
                "workspace_id": "workspace_dashpro",
                "goal": "Ship parent fees",
            },
            {
                "plan_id": "p2",
                "workspace_id": "workspace_dashpro",
                "goal": "Twin same company",
            },
            {
                "plan_id": "p3",
                "workspace_id": "workspace_axon_watch",
                "goal": "Fast Gate",
            },
        ]
        statuses: list[tuple[str, str]] = []

        def _set_status(plan_id: str, status: str) -> dict[str, str]:
            statuses.append((plan_id, status))
            return {"plan_id": plan_id, "status": status}

        with (
            patch(
                "app.persistence.operator_presence_settings_store.load_settings",
                return_value={"autonomy_mode": "full"},
            ),
            patch(
                "app.workspace_agents.lead_vaxon_handoff.list_awaiting_engagement_plans",
                return_value=plans,
            ),
            patch(
                "app.workspace_agents.lead_plan_store.set_plan_status",
                side_effect=_set_status,
            ),
            patch(
                "app.workspace_agents.lead_plan_store.append_receipt",
                return_value={},
            ),
        ):
            result = engage_awaiting_lead_plans(max_plans=5, require_full_autonomy=True)
        self.assertTrue(result["ok"])
        self.assertEqual(len(result["engaged"]), 2)
        self.assertEqual({row[0] for row in statuses}, {"p1", "p3"})
        self.assertTrue(all(row[1] == "completed" for row in statuses))


if __name__ == "__main__":
    unittest.main()