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
    is_axon_x_mobile_companion_goal,
    should_execute_lead_fast_path,
    should_lead_decompose_dispatch,
)
from app.workspace_agents.lead_query_intent import detect_specialist_query_intent  # noqa: E402


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

    def test_domain_agnostic_goal_flags_ambiguous_instead_of_confident_fan_out(self) -> None:
        # Regression: a plain content-editing task (no API/database/signals system
        # involved at all) that happens to contain a couple of generic words each
        # role's keyword bag matches ("service", "data", "health", "signal") used to
        # be treated as confidently decisive multi-domain work purely because two
        # roles cleared the bare MIN_WINNER_SCORE — this is the exact failure that
        # fanned a childcare-menu task out to mismatched Backend + Watcher specialists.
        plan = build_lead_task_plan(
            goal=(
                "Rearrange the existing weekly menu items and update the room roster "
                "service data, keeping an eye on child health signals throughout."
            ),
            roster=DASHPRO_ROSTER,
            mode="decompose",
        )
        self.assertTrue(plan.ambiguous)
        roles = sorted(item.owner_role for item in plan.items)
        self.assertEqual(["backend", "watcher"], roles)

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

    def test_tenant_headcount_routes_from_lead_to_backend(self) -> None:
        goal = "How many children do we have in the Young Eagles preschool tenant?"
        plan = build_lead_task_plan(
            goal=goal,
            roster=DASHPRO_ROSTER,
            mode="decompose",
        )

        self.assertTrue(detect_specialist_query_intent(goal))
        self.assertTrue(should_lead_decompose_dispatch(plan))
        self.assertEqual(["backend"], [item.owner_role for item in plan.items])

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

    def test_axon_x_expo_companion_prompt_is_implementation_intent(self) -> None:
        goal = (
            "I found the mobile UI; now I want Mira and her team to continue "
            "working on it in an Expo native app, fix Mira's plan, clear old "
            "stale runs, and upgrade the agents where possible."
        )

        plan = build_lead_task_plan(goal=goal, roster=DASHPRO_ROSTER, mode="decompose")

        self.assertTrue(detect_implement_intent(goal))
        self.assertTrue(should_execute_lead_fast_path("plan", goal))
        self.assertTrue(should_lead_decompose_dispatch(plan))
        self.assertIn("frontend", [item.owner_role for item in plan.items])

    def test_axon_x_mobile_companion_short_correction_gets_exact_app_contract(self) -> None:
        goal = "I meant the mobile app -"

        plan = build_lead_task_plan(
            goal=goal,
            roster=DASHPRO_ROSTER,
            mode="decompose",
            workspace_id="workspace_axon_watch",
        )

        self.assertTrue(is_axon_x_mobile_companion_goal(goal, "workspace_axon_watch"))
        self.assertFalse(is_axon_x_mobile_companion_goal(goal, "workspace_dashpro"))
        self.assertFalse(plan.ambiguous)
        self.assertTrue(should_lead_decompose_dispatch(plan))
        self.assertEqual(["frontend"], [item.owner_role for item in plan.items])
        self.assertIn("apps/console-mobile", plan.goal)
        self.assertIn("workspace_axon_watch", plan.goal)
        self.assertIn("DashPro", plan.goal)
        self.assertIn("127.0.0.1", plan.goal)
        self.assertEqual(
            ["apps/console-mobile", "package.json", "package-lock.json", "README.md"],
            plan.items[0].allowed_paths,
        )
        self.assertIn(
            "npm run typecheck -w @axon-watch/console-mobile",
            plan.items[0].acceptance_criteria,
        )
        self.assertIn(
            "expo config --json",
            plan.items[0].acceptance_criteria,
        )

    def test_plan_mode_review_language_stays_consultative(self) -> None:
        goal = "Before I run this prompt, check Mira's plan and advice on that"

        self.assertFalse(detect_implement_intent(goal))
        self.assertFalse(should_execute_lead_fast_path("plan", goal))
        self.assertTrue(should_execute_lead_fast_path("agent", goal))

    def test_git_privacy_policy_routes_to_integrations_with_root_scope(self) -> None:
        plan = build_lead_task_plan(
            goal=(
                "Harden TPS Git privacy controls: update root .gitignore, "
                "and project.axon.yaml deny-list."
            ),
            roster=DASHPRO_ROSTER,
            mode="sequential",
        )

        self.assertEqual(["integrations"], [item.owner_role for item in plan.items])
        self.assertEqual(
            [".gitignore", "project.axon.yaml"],
            plan.items[0].allowed_paths,
        )

    def test_parent_dashboard_ux_improvement_dispatches_to_frontend(self) -> None:
        goal = (
            "In the parents Dashboard - this screen doesn't make sense - what are "
            "the parents submitting - and what is the teacher going to see - please "
            "make it make sense and improve it"
        )

        plan = build_lead_task_plan(goal=goal, roster=DASHPRO_ROSTER, mode="decompose")

        self.assertTrue(detect_implement_intent(goal))
        self.assertFalse(plan.ambiguous)
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
