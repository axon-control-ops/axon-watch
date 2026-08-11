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
    detect_implement_intent,
    extract_exclusive_paths,
    should_lead_decompose_dispatch,
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
        self.assertTrue(detect_fan_out_intent("Oi assign all the agents to start working"))
        self.assertTrue(detect_fan_out_intent("assign all agents to start working"))
        self.assertTrue(detect_fan_out_intent("get all the agents working"))
        self.assertFalse(detect_fan_out_intent("Fix the backend API heap calc"))
        self.assertFalse(detect_fan_out_intent("Assign Marco the heap-calc fix only"))

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

    def test_auto_defaults_to_decompose_not_broadcast(self) -> None:
        plan = build_lead_task_plan(
            goal="Fix the quality-gate API failure and the enrollment confirmation popup",
            roster=DASHPRO_ROSTER,
            mode="auto",
        )
        self.assertEqual("decompose", plan.mode)
        roles = sorted(item.owner_role for item in plan.items)
        self.assertEqual(["backend", "frontend"], roles)
        self.assertNotIn("watcher", roles)
        self.assertNotIn("integrations", roles)
        goals = {item.owner_role: item.goal for item in plan.items}
        self.assertIn("Frontend:", goals["frontend"])
        self.assertIn("Backend:", goals["backend"])
        self.assertNotEqual(goals["frontend"], goals["backend"])

    def test_dashboard_plus_idempotency_data_cleanup_splits_frontend_and_backend(self) -> None:
        plan = build_lead_task_plan(
            goal=(
                "Fix the dashboard UI and assignment idempotency/data cleanup so "
                "duplicate assignments stop and parent-delivery data is correct."
            ),
            roster=DASHPRO_ROSTER,
            mode="decompose",
        )

        roles = sorted(item.owner_role for item in plan.items)
        self.assertEqual(["backend", "frontend"], roles)
        goals = {item.owner_role: item.goal for item in plan.items}
        self.assertIn("Frontend:", goals["frontend"])
        self.assertIn("Backend:", goals["backend"])

    def test_decompose_then_clause_chains_dependencies(self) -> None:
        plan = build_lead_task_plan(
            goal="Fix the API quality-gate heap calc then update the Expo confirmation screen",
            roster=DASHPRO_ROSTER,
            mode="decompose",
        )
        self.assertEqual("decompose", plan.mode)
        self.assertGreaterEqual(len(plan.items), 2)
        self.assertEqual("backend", plan.items[0].owner_role)
        self.assertEqual("frontend", plan.items[1].owner_role)
        self.assertEqual([plan.items[0].plan_key], plan.items[1].dependencies)

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
        for item in plan.items:
            if item.exclusive_paths:
                self.assertEqual(item.exclusive_paths, item.allowed_paths)

    def test_extract_exclusive_paths_includes_frontend_hooks(self) -> None:
        paths = extract_exclusive_paths(
            "Fix hooks/homework/usePracticeAtHome.ts and components/HomeworkCard.tsx"
        )

        self.assertIn("hooks/homework/usePracticeAtHome.ts", paths)
        self.assertIn("components/HomeworkCard.tsx", paths)

    def test_should_lead_decompose_dispatch(self) -> None:
        multi = build_lead_task_plan(
            goal="Fix the quality-gate API failure and the enrollment confirmation popup",
            roster=DASHPRO_ROSTER,
            mode="decompose",
        )
        self.assertTrue(should_lead_decompose_dispatch(multi))
        single = build_lead_task_plan(
            goal="Fix the enrollment confirmation popup",
            roster=DASHPRO_ROSTER,
            mode="decompose",
        )
        self.assertTrue(should_lead_decompose_dispatch(single))
        fan = build_lead_task_plan(
            goal="Check with all sub-agents about memory",
            roster=DASHPRO_ROSTER,
            mode="auto",
        )
        self.assertFalse(should_lead_decompose_dispatch(fan))

    def test_dashpro_dashboard_fixes_dispatch_to_frontend(self) -> None:
        goal = (
            "I ran the dev server - but I still don't see any changes in the teachers "
            "dashboard - and in the parent dashboard - can you please make the fixes "
            "end to end - and stop at nothing until this is fixed"
        )

        plan = build_lead_task_plan(goal=goal, roster=DASHPRO_ROSTER, mode="decompose")

        self.assertTrue(detect_implement_intent(goal))
        self.assertTrue(should_lead_decompose_dispatch(plan))
        self.assertEqual(["frontend"], [item.owner_role for item in plan.items])

    def test_shift_retry_skips_lead_decompose_dispatch(self) -> None:
        from app.workspace_agents.lead_task_plan import is_employee_shift_retry_request

        retry = (
            "My last continuous shift on Axon-X priorities failed. "
            "Last error: Workspace delivery blocked: missing or failing "
            "acceptance_evidence (Gate 6). Retry that bounded shift now as me."
        )
        self.assertTrue(is_employee_shift_retry_request(retry))
        plan = build_lead_task_plan(
            goal=retry,
            roster=DASHPRO_ROSTER,
            mode="decompose",
        )
        self.assertFalse(should_lead_decompose_dispatch(plan))

    def test_empty_goal_raises(self) -> None:
        with self.assertRaises(ValueError):
            build_lead_task_plan(goal="  ", roster=DASHPRO_ROSTER)


if __name__ == "__main__":
    unittest.main()
