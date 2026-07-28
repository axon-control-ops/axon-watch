from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.chat.lane_b_agent import LaneBContext, build_lane_b_context_block  # noqa: E402
from app.cli_runtime.router import _build_prompt  # noqa: E402
from app.workspace_agents.employee_persona_prompt import (  # noqa: E402
    EMPLOYEE_PERSONA_MARKER,
    adapt_lane_b_system_prompt_for_employee,
    build_employee_identity_line,
    build_employee_persona_appendix,
    find_roster_employee,
    split_employee_persona_from_context,
)
from app.workspace_agents.worker_prompt import build_continuous_worker_prompt  # noqa: E402
from app.workspace_agents.config_loader import EmployeeConfig  # noqa: E402


class EmployeePersonaPromptTests(unittest.TestCase):
    def test_identity_line_shape(self) -> None:
        line = build_employee_identity_line(
            workspace_id="workspace_axon_watch",
            name="Quinn",
            role="integrations",
            owns="connectors, watch service, and cross-repo wiring",
        )
        self.assertIn("You are Quinn. Your role is integrations for workspace workspace_axon_watch.", line)
        self.assertIn("You own: connectors, watch service, and cross-repo wiring.", line)
        self.assertIn("Always speak in first person", line)

    def test_appendix_none_without_employee_id(self) -> None:
        self.assertIsNone(
            build_employee_persona_appendix(
                workspace_id="workspace_axon_watch",
                employee_id=None,
            )
        )
        self.assertIsNone(
            build_employee_persona_appendix(
                workspace_id="workspace_axon_watch",
                employee_id="  ",
            )
        )

    def test_appendix_uses_roster_employee(self) -> None:
        roster_row = {
            "employee_id": "employee-workspace_axon_watch-integrations-4",
            "name": "Quinn",
            "role": "integrations",
            "role_label": "Integrations",
            "owns": "connectors, watch service, and cross-repo wiring",
        }
        with patch(
            "app.workspace_agents.employee_persona_prompt.find_roster_employee",
            return_value=roster_row,
        ), patch(
            "app.workspace_agents.employee_persona_prompt.build_team_roster_context",
            return_value=(
                "Company team roster (authoritative — do not search the repo for this):\n"
                "- Quinn (Integrations / integrations) — owns: connectors"
            ),
        ):
            appendix = build_employee_persona_appendix(
                workspace_id="workspace_axon_watch",
                employee_id="employee-workspace_axon_watch-integrations-4",
                employee_role="integrations",
            )
        assert appendix is not None
        self.assertIn("Employee persona (authoritative for this thread)", appendix)
        self.assertIn("You are Quinn", appendix)
        self.assertIn("Role label: Integrations", appendix)
        self.assertIn("not as VAXON", appendix)
        self.assertIn("say which role should own it", appendix)
        self.assertIn("frontend, backend, integrations, watcher, or lead", appendix)
        self.assertIn("Company team roster (authoritative", appendix)

    def test_lead_appendix_includes_authoritative_team_and_no_search_clause(self) -> None:
        roster_row = {
            "employee_id": "employee-workspace_dashpro-lead-0",
            "name": "Dana",
            "role": "lead",
            "role_label": "Lead",
            "owns": "DashPro product priorities and handoffs",
        }
        with patch(
            "app.workspace_agents.employee_persona_prompt.find_roster_employee",
            return_value=roster_row,
        ), patch(
            "app.workspace_agents.employee_persona_prompt.build_team_roster_context",
            return_value=(
                "Company team roster (authoritative — do not search the repo for this):\n"
                "- Dana (Lead / lead)[LEAD] — owns: priorities\n"
                "- Priya (Frontend / frontend) — owns: payments UI\n"
                "Do NOT Glob, Grep, or Read the filesystem to discover teammates"
            ),
        ):
            appendix = build_employee_persona_appendix(
                workspace_id="workspace_dashpro",
                employee_id="employee-workspace_dashpro-lead-0",
                employee_role="lead",
            )
        assert appendix is not None
        self.assertIn("You are Dana. Your role is lead", appendix)
        self.assertIn("never rediscover staffing by searching the tree", appendix)
        self.assertIn("Here's where things stand and what I changed.", appendix)
        self.assertIn("Priya (Frontend / frontend)", appendix)
        self.assertIn("Do NOT Glob, Grep, or Read", appendix)

    def test_specialist_appendix_requires_lead_handoff_without_name_stamping(self) -> None:
        roster_row = {
            "employee_id": "employee-workspace_dashpro-frontend-1",
            "name": "Priya",
            "role": "frontend",
            "role_label": "Frontend",
            "owns": "payments UI",
        }
        with patch(
            "app.workspace_agents.employee_persona_prompt.find_roster_employee",
            return_value=roster_row,
        ), patch(
            "app.workspace_agents.employee_persona_prompt.build_team_roster_context",
            return_value="",
        ):
            appendix = build_employee_persona_appendix(
                workspace_id="workspace_dashpro",
                employee_id="employee-workspace_dashpro-frontend-1",
                employee_role="frontend",
            )
        assert appendix is not None
        self.assertIn("report finished work to your company Lead", appendix)
        self.assertIn("Never announce your name or role mid-reply", appendix)
        self.assertIn("Sir King", appendix)
        self.assertIn("On it", appendix)
        self.assertIn("my last shift receipts", appendix)
        self.assertIn('e.g. "Pulling my last shift receipts now, Sir King."', appendix)
        self.assertNotIn('e.g. "Pulling Priya\'s shift receipts now, Sir King."', appendix)
        self.assertIn("Never speak about yourself in the third person", appendix)
        self.assertIn("I am doing this as Priya", appendix)
        self.assertIn("I am wiring Copy Link", appendix)
        self.assertIn("Priya is planning", appendix)
        self.assertIn("I am planning activities and assignments", appendix)

    def test_appendix_fallback_when_roster_misses(self) -> None:
        with patch(
            "app.workspace_agents.employee_persona_prompt.find_roster_employee",
            return_value=None,
        ), patch(
            "app.workspace_agents.employee_persona_prompt.build_team_roster_context",
            return_value="",
        ):
            appendix = build_employee_persona_appendix(
                workspace_id="workspace_axon_watch",
                employee_id="employee-unknown",
                employee_role="frontend",
            )
        assert appendix is not None
        self.assertIn("Jules", appendix)  # default frontend name
        self.assertIn("frontend", appendix)

    def test_persona_lands_in_lane_b_context_block(self) -> None:
        appendix = build_employee_persona_appendix(
            workspace_id="workspace_axon_watch",
            employee_id="employee-workspace_axon_watch-integrations-4",
            employee_role="integrations",
        )
        assert appendix is not None
        block = build_lane_b_context_block(
            LaneBContext(
                workspace_id="workspace_axon_watch",
                composer_mode="agent",
                memory_appendix=appendix,
            )
        )
        self.assertIn("You are Quinn", block)
        self.assertIn("Employee persona (authoritative for this thread)", block)

    def test_find_roster_employee_live(self) -> None:
        found = find_roster_employee(
            "workspace_axon_watch",
            "employee-workspace_axon_watch-integrations-4",
        )
        assert found is not None
        self.assertEqual("Quinn", found.get("name"))

    def test_continuous_worker_still_uses_shared_identity(self) -> None:
        with patch(
            "app.workspace_agents.worker_prompt.build_team_roster_context",
            return_value="",
        ):
            prompt = build_continuous_worker_prompt(
                workspace_id="workspace_axon_watch",
                employee=EmployeeConfig(
                    name="Shell Craft",
                    role="frontend",
                    owns="Vue shell and IDE polish",
                    schedule="continuous",
                ),
            )
        self.assertIn(
            "You are Shell Craft. Your role is frontend for workspace workspace_axon_watch.",
            prompt,
        )
        self.assertIn("Always speak in first person", prompt)

    def test_split_elevates_persona_and_keeps_memory(self) -> None:
        appendix = build_employee_persona_appendix(
            workspace_id="workspace_axon_watch",
            employee_id="employee-workspace_axon_watch-integrations-4",
            employee_role="integrations",
        )
        assert appendix is not None
        context = f"Workspace: workspace_axon_watch\n\n{appendix}\n\nKAIRO memory (non-authoritative):\n- Task: keep going"
        persona, remainder = split_employee_persona_from_context(context)
        assert persona is not None
        self.assertTrue(persona.startswith(EMPLOYEE_PERSONA_MARKER))
        self.assertIn("You are Quinn", persona)
        self.assertIn("KAIRO memory", remainder)
        self.assertNotIn(EMPLOYEE_PERSONA_MARKER, remainder)

    def test_adapt_system_prompt_rewrites_lane_b_identity(self) -> None:
        appendix = build_employee_persona_appendix(
            workspace_id="workspace_axon_watch",
            employee_id="employee-workspace_axon_watch-integrations-4",
            employee_role="integrations",
        )
        original = "You are Axon-X Lane B in Agent mode with Full Access. Tool execution is allowed."
        adapted = adapt_lane_b_system_prompt_for_employee(original, appendix)
        self.assertIn("named employee in the Employee persona block", adapted)
        self.assertNotIn("You are Axon-X Lane B in Agent mode with Full Access.", adapted)
        self.assertIn("Do not identify as VAXON", adapted)
        self.assertIn("first person", adapted)
        unchanged = adapt_lane_b_system_prompt_for_employee(original, "no persona here")
        self.assertEqual(original, unchanged)

    def test_build_prompt_elevates_persona_above_workspace_context(self) -> None:
        appendix = build_employee_persona_appendix(
            workspace_id="workspace_axon_watch",
            employee_id="employee-workspace_axon_watch-integrations-4",
            employee_role="integrations",
        )
        assert appendix is not None
        context = build_lane_b_context_block(
            LaneBContext(
                workspace_id="workspace_axon_watch",
                composer_mode="agent",
                memory_appendix=appendix,
            )
        )
        prompt = _build_prompt(
            composer_mode="agent",
            user_prompt="Retry the last failed shift and summarize receipts.",
            context_block=context,
            execution_tier="executing",
        )
        self.assertIn("You are Quinn", prompt)
        self.assertIn("named employee in the Employee persona block", prompt)
        self.assertNotIn(
            "You are Axon-X Lane B in Agent mode with Full Access.",
            prompt,
        )
        persona_at = prompt.index(EMPLOYEE_PERSONA_MARKER)
        workspace_at = prompt.index("Workspace context:")
        request_at = prompt.index("Operator request:")
        self.assertLess(persona_at, workspace_at)
        self.assertLess(workspace_at, request_at)


if __name__ == "__main__":
    unittest.main()
