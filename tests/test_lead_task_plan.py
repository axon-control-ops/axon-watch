"""Gate 5 Lead planner — goal → ordered task plan (pure function)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.workspace_agents.lead_task_plan import (  # noqa: E402
    build_lead_task_plan,
    detect_fan_out_intent,
    extract_exclusive_paths,
)


DASHPRO_ROSTER = [
    {"role": "lead", "name": "Dana", "owns": "CI triage and handoffs"},
    {"role": "watcher", "name": "Rowan", "owns": "signals and health"},
    {"role": "frontend", "name": "Shell Craft", "owns": "UI and Expo"},
    {"role": "backend", "name": "Marco", "owns": "APIs and persistence"},
    {"role": "integrations", "name": "Soren", "owns": "CI and connectors"},
]


class LeadTaskPlanTests(unittest.TestCase):
    def test_detect_fan_out_intent(self) -> None:
        self.assertTrue(detect_fan_out_intent("Dana, check with all sub-agents about memory"))
        self.assertTrue(detect_fan_out_intent("Ask every teammate for a status"))
        self.assertFalse(detect_fan_out_intent("Fix the backend API heap calc"))

    def test_fan_out_creates_parallel_specialist_tasks(self) -> None:
        plan = build_lead_task_plan(
            goal="Check with all sub-agents whether DashPro quality-gate heap calc is safe",
            roster=DASHPRO_ROSTER,
            mode="auto",
        )
        self.assertEqual("fan_out", plan.mode)
        roles = sorted(item.owner_role for item in plan.items)
        self.assertEqual(["backend", "frontend", "integrations", "watcher"], roles)
        # No lead tasks; deps empty unless path conflict serializes.
        self.assertTrue(all(item.owner_role != "lead" for item in plan.items))

    def test_sequential_then_clause_chains_dependencies(self) -> None:
        plan = build_lead_task_plan(
            goal="Fix the API quality-gate heap calc then update the Expo confirmation screen",
            roster=DASHPRO_ROSTER,
            mode="sequential",
        )
        self.assertEqual("sequential", plan.mode)
        self.assertGreaterEqual(len(plan.items), 2)
        self.assertEqual("backend", plan.items[0].owner_role)
        self.assertEqual("frontend", plan.items[1].owner_role)
        self.assertEqual([plan.items[0].plan_key], plan.items[1].dependencies)
        self.assertEqual(
            [plan.items[0].plan_key, plan.items[1].plan_key],
            plan.ordered_keys,
        )

    def test_overlapping_paths_serialize_fan_out(self) -> None:
        plan = build_lead_task_plan(
            goal="Check with all teammates about apps/console-web/src/stores/shell.ts",
            roster=DASHPRO_ROSTER,
            mode="fan_out",
        )
        paths = extract_exclusive_paths(plan.goal)
        self.assertIn("apps/console-web/src/stores/shell.ts", paths)
        # First specialist owns the path; later ones that share it depend on earlier keys.
        keyed = {item.plan_key: item for item in plan.items}
        with_deps = [item for item in plan.items if item.dependencies]
        self.assertTrue(with_deps)
        for item in with_deps:
            for dep in item.dependencies:
                self.assertIn(dep, keyed)

    def test_empty_goal_raises(self) -> None:
        with self.assertRaises(ValueError):
            build_lead_task_plan(goal="  ", roster=DASHPRO_ROSTER)


if __name__ == "__main__":
    unittest.main()
