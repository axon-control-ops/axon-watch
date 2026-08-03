from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.kairo.mission_spec import (  # noqa: E402
    MISSION_SPEC_FIELDS,
    build_mission_spec,
    format_mission_spec,
)
from app.kairo.specialty_action_reply import build_specialty_action_reply  # noqa: E402


class KairoMissionSpecTests(unittest.TestCase):
    def test_builds_every_standard_field_from_lead_plan(self) -> None:
        action = {
            "type": "lead_fan_out",
            "plan_id": "lead-plan-auth",
            "plan": {
                "items": [
                    {
                        "goal": "Build login UI",
                        "owner_role": "frontend",
                        "acceptance_criteria": "Login screen passes accessibility checks.",
                        "dependencies": [],
                        "allowed_paths": ["apps/console-web/src"],
                    },
                    {
                        "goal": "Implement session API",
                        "owner_role": "backend",
                        "acceptance_criteria": "Session tests pass.",
                        "dependencies": ["frontend"],
                        "allowed_paths": ["services/control-plane/app"],
                    },
                ]
            },
        }

        spec = build_mission_spec(
            task="Mission: Build authentication",
            workspace_id="workspace_axon_watch",
            action=action,
        )

        self.assertEqual("lead-plan-auth", spec["mission_id"])
        self.assertEqual({key for key, _label in MISSION_SPEC_FIELDS}, set(spec))
        self.assertIn("frontend", spec["recommended_specialists"])
        self.assertIn("backend", spec["recommended_specialists"])
        self.assertIn("Build login UI", spec["deliverables"])
        self.assertIn("Session tests pass", spec["success_criteria"])
        self.assertIn("Medium", spec["estimated_complexity"])

        rendered = format_mission_spec(spec, evidence_state="Dispatched")
        self.assertTrue(rendered.startswith("Dispatched: Mission Specification"))
        for _key, label in MISSION_SPEC_FIELDS:
            self.assertIn(f"**{label}:**", rendered)

        reply, spoken = build_specialty_action_reply(
            {
                **action,
                "mode": "fan_out",
                "tasks": [{"task_id": "front"}, {"task_id": "back"}],
                "mission_spec": spec,
            }
        )
        self.assertIn("Dispatched: Mission Specification", reply)
        self.assertIn("Dispatch evidence", reply)
        self.assertTrue(spoken.startswith("Dispatched:"))

    def test_respects_explicit_mission_fields(self) -> None:
        spec = build_mission_spec(
            task=(
                "Mission Title: Auth hardening\n"
                "Objective: Reduce account takeover risk\n"
                "Business Context: Prepare for launch\n"
                "Definition of Done: Security review verified"
            ),
            workspace_id="workspace_axon_watch",
            action={"type": "route_employee", "employee_role": "backend"},
        )

        self.assertEqual("Auth hardening", spec["mission_title"])
        self.assertEqual("Reduce account takeover risk", spec["objective"])
        self.assertEqual("Prepare for launch", spec["business_context"])
        self.assertEqual("Security review verified", spec["definition_of_done"])


if __name__ == "__main__":
    unittest.main()
