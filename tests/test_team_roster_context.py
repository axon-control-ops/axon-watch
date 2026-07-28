from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.workspace_agents.team_roster_context import (  # noqa: E402
    TEAM_ROSTER_MARKER,
    build_team_roster_context,
    format_team_roster_block,
)


class TeamRosterContextTests(unittest.TestCase):
    def test_format_lead_block_lists_members_and_forbids_search(self) -> None:
        company = {
            "workspace_id": "workspace_dashpro",
            "company_name": "DashPro",
            "employees": [
                {
                    "employee_id": "employee-workspace_dashpro-lead-0",
                    "name": "Dana",
                    "role": "lead",
                    "role_label": "Lead",
                    "owns": "product priorities and handoffs",
                    "schedule": "on_demand",
                    "status": "idle",
                    "enabled": True,
                    "primary": True,
                },
                {
                    "employee_id": "employee-workspace_dashpro-frontend-2",
                    "name": "Priya",
                    "role": "frontend",
                    "role_label": "Frontend",
                    "owns": "payments UI",
                    "schedule": "continuous",
                    "status": "idle",
                    "enabled": True,
                    "primary": False,
                    "last_outcome": "failed",
                    "last_outcome_detail": "usage limits blocked the agent runtime",
                },
            ],
        }
        block = format_team_roster_block(company, viewer_role="lead")
        self.assertIn(TEAM_ROSTER_MARKER, block)
        self.assertIn("Dana (Lead / lead) [LEAD]", block)
        self.assertIn("owns: product priorities and handoffs", block)
        self.assertIn("Priya (Frontend / frontend)", block)
        self.assertIn("last job failed: usage limits blocked the agent runtime", block)
        self.assertIn("Do NOT Glob, Grep, or Read", block)

    def test_format_specialist_block_is_compact(self) -> None:
        company = {
            "workspace_id": "workspace_dashpro",
            "company_name": "DashPro",
            "employees": [
                {
                    "name": "Dana",
                    "role": "lead",
                    "role_label": "Lead",
                    "owns": "priorities",
                    "primary": True,
                },
                {
                    "name": "Marco",
                    "role": "backend",
                    "role_label": "Backend",
                    "owns": "APIs",
                },
            ],
        }
        block = format_team_roster_block(company, viewer_role="backend")
        self.assertIn(TEAM_ROSTER_MARKER, block)
        self.assertIn("Marco (Backend / backend)", block)
        self.assertNotIn("Do NOT Glob, Grep, or Read", block)
        self.assertIn("handoffs and role boundaries", block)
        self.assertNotIn("schedule:", block)

    def test_format_empty_company_returns_empty(self) -> None:
        self.assertEqual(format_team_roster_block(None), "")
        self.assertEqual(format_team_roster_block({"employees": []}), "")

    def test_build_team_roster_context_uses_company_roster(self) -> None:
        with patch(
            "app.workspace_agents.build_company_roster",
            return_value={
                "workspace_id": "workspace_dashpro",
                "company_name": "DashPro",
                "employees": [
                    {
                        "name": "Dana",
                        "role": "lead",
                        "role_label": "Lead",
                        "owns": "priorities",
                        "primary": True,
                    }
                ],
            },
        ):
            block = build_team_roster_context("workspace_dashpro", viewer_role="lead")
        self.assertIn(TEAM_ROSTER_MARKER, block)
        self.assertIn("Dana", block)


if __name__ == "__main__":
    unittest.main()
