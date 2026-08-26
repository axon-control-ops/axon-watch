"""Gate 5 — persist Lead plan + materialize fan-out runs."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

from tests.support.control_plane_app_loader import prepare_control_plane_imports
from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))


class LeadFanOutMaterializeTests(unittest.TestCase):
    def setUp(self) -> None:
        self._saved = prepare_control_plane_imports()
        self.addCleanup(self._restore)
        from app.persistence import chat_store, run_store, task_store

        isolate_control_plane_db(self, run_store)
        chat_store.reset_store()
        task_store.reset_store()
        self.addCleanup(chat_store.reset_store)
        self.addCleanup(task_store.reset_store)

    def _restore(self) -> None:
        for name in list(sys.modules):
            if name == "app" or name.startswith("app."):
                del sys.modules[name]
        sys.modules.update(self._saved)

    def test_persist_maps_plan_keys_to_task_ids(self) -> None:
        from app.workspace_agents.lead_task_persist import persist_lead_task_plan
        from app.workspace_agents.lead_task_plan import build_lead_task_plan

        plan = build_lead_task_plan(
            goal="Fix the API heap calc then update the Expo confirmation screen",
            roster=[
                {"role": "lead", "name": "Dana"},
                {"role": "backend", "name": "Marco", "owns": "APIs"},
                {"role": "frontend", "name": "Shell", "owns": "UI"},
            ],
            mode="sequential",
        )
        persisted = persist_lead_task_plan(
            workspace_id="workspace_axon_watch",
            plan=plan,
        )
        self.assertEqual(len(plan.items), len(persisted["tasks"]))
        self.assertEqual(
            set(persisted["plan_key_to_task_id"]),
            {item.plan_key for item in plan.items},
        )
        first_task = persisted["tasks"][0]
        second_task = persisted["tasks"][1]
        self.assertEqual([], first_task["dependencies"])
        self.assertEqual(
            [persisted["plan_key_to_task_id"][plan.items[0].plan_key]],
            second_task["dependencies"],
        )

    def test_fan_out_opens_concurrent_ready_runs(self) -> None:
        from app.persistence import run_store, task_store
        from app.workspace_agents.lead_fan_out import materialize_lead_fan_out

        result = materialize_lead_fan_out(
            workspace_id="workspace_axon_watch",
            goal="Check with all sub-agents whether Gate 5 fan-out is wired",
            mode="auto",
            create_runs=True,
        )
        self.assertEqual("fan_out", result["mode"])
        self.assertTrue(result["fan_out_intent"])
        self.assertGreaterEqual(len(result["tasks"]), 3)
        # No path overlap → all specialists ready in parallel.
        self.assertEqual(len(result["deferred"]), 0)
        self.assertEqual(len(result["runs"]), len(result["tasks"]))
        roles = sorted(str(run["owner_role"]) for run in result["runs"])
        self.assertIn("backend", roles)
        self.assertIn("frontend", roles)
        for run in result["runs"]:
            stored = run_store.get_run(str(run["run_id"]))
            self.assertIsNotNone(stored)
            assert stored is not None
            self.assertEqual(run["task_id"], stored.get("task_id"))
            self.assertEqual("queued", stored.get("phase"))
            history = run_store.list_history(stored["history_ref"])
            types = [
                str(item.get("receipt", {}).get("type") or "") for item in history
            ]
            self.assertIn("lead_fan_out_assigned", types)
            task = task_store.get_task(str(run["task_id"]))
            self.assertIsNotNone(task)
            assert task is not None
            self.assertEqual("leased", task["status"])

    def test_fan_out_tasks_carry_operator_attachment_ids(self) -> None:
        from app.workspace_agents.lead_fan_out import materialize_lead_fan_out

        result = materialize_lead_fan_out(
            workspace_id="workspace_axon_watch",
            goal="Ask all teammates to inspect the two attached screenshots and improve the site",
            mode="fan_out",
            create_runs=False,
            attachment_ids=["attachment_one", "attachment_two"],
        )

        self.assertGreaterEqual(len(result["tasks"]), 1)
        for task in result["tasks"]:
            self.assertEqual(["attachment_one", "attachment_two"], task["attachment_ids"])

    def test_path_overlap_defers_dependent_runs(self) -> None:
        from app.workspace_agents.lead_fan_out import materialize_lead_fan_out

        result = materialize_lead_fan_out(
            workspace_id="workspace_axon_watch",
            goal=(
                "Check with all teammates about "
                "apps/console-web/src/stores/shell.ts"
            ),
            mode="fan_out",
            create_runs=True,
        )
        self.assertEqual("fan_out", result["mode"])
        self.assertGreaterEqual(len(result["deferred"]), 1)
        self.assertGreaterEqual(len(result["runs"]), 1)
        self.assertEqual(
            len(result["runs"]) + len(result["deferred"]),
            len(result["tasks"]),
        )

    def test_specialist_can_assign_one_colleague_without_lead_planning(self) -> None:
        from app.workspace_agents.lead_fan_out import materialize_lead_fan_out

        result = materialize_lead_fan_out(
            workspace_id="workspace_axon_watch",
            goal="Implement the persistence guard in services/control-plane/app/store.py",
            target_role="backend",
            create_runs=True,
            use_model=False,
        )

        self.assertEqual("backend", result["target_role"])
        self.assertEqual("decompose", result["mode"])
        self.assertEqual(1, len(result["tasks"]))
        self.assertEqual("backend", result["tasks"][0]["owner_role"])
        self.assertEqual(1, len(result["runs"]))
        self.assertEqual("backend", result["runs"][0]["owner_role"])

    def test_direct_assignment_rejects_an_unstaffed_role(self) -> None:
        from app.persistence import task_store
        from app.workspace_agents.lead_fan_out import (
            LeadFanOutError,
            materialize_lead_fan_out,
        )

        existing = task_store.create_task(
            workspace_id="workspace_axon_watch",
            goal="Do specialist work",
            owner_role="backend",
        )
        with self.assertRaisesRegex(LeadFanOutError, "not staffed"):
            materialize_lead_fan_out(
                workspace_id="workspace_axon_watch",
                goal="Do specialist work",
                target_role="finance",
                create_runs=False,
                use_model=False,
            )
        stored = task_store.get_task(str(existing["task_id"]))
        self.assertIsNotNone(stored)
        self.assertEqual("open", stored and stored["status"])

    def test_direct_assignment_only_supersedes_the_target_colleagues_duplicate(self) -> None:
        from app.persistence import task_store
        from app.workspace_agents.lead_fan_out import materialize_lead_fan_out

        goal = "Implement the shared persistence safeguard for recurring task records"
        frontend = task_store.create_task(
            workspace_id="workspace_axon_watch",
            goal=goal,
            owner_role="frontend",
        )
        backend = task_store.create_task(
            workspace_id="workspace_axon_watch",
            goal=goal,
            owner_role="backend",
        )

        materialize_lead_fan_out(
            workspace_id="workspace_axon_watch",
            goal=goal,
            target_role="backend",
            create_runs=False,
            use_model=False,
        )

        stored_frontend = task_store.get_task(str(frontend["task_id"]))
        stored_backend = task_store.get_task(str(backend["task_id"]))
        self.assertEqual("open", stored_frontend and stored_frontend["status"])
        self.assertEqual("cancelled", stored_backend and stored_backend["status"])

    def test_route_teammate_does_not_pick_single_winner_on_fan_out(self) -> None:
        from app.workspace_agents.teammate_route import route_teammate_decision

        decision = route_teammate_decision(
            workspace_id="workspace_axon_watch",
            prompt="Dana, check with all sub-agents about memory leaks",
            use_model_tiebreak=False,
        )
        self.assertFalse(decision.should_route)
        self.assertEqual("lead_fan_out", decision.reason)
        self.assertEqual("lead_planner", decision.source)

    def test_named_multi_role_dispatch_stays_with_lead(self) -> None:
        from app.workspace_agents.teammate_route import route_teammate_decision

        decision = route_teammate_decision(
            workspace_id="workspace_dashpro",
            current_employee_id="employee-workspace_dashpro-lead-0",
            prompt=(
                "The three tasks from this morning are still open — "
                "task-ec42c713997048aa, task-c3f1c233ea184ade, and "
                "task-138a5dec16bf4ddf — they were never dispatched. Assign the "
                "two UI tasks to Priya (frontend) and the teacher query task to "
                "the backend specialist now. Use materialize_lead_fan_out with "
                "create_runs=True or directly lease those tasks and create queued runs."
            ),
            use_model_tiebreak=False,
        )
        self.assertFalse(decision.should_route)
        self.assertEqual("lead_fan_out", decision.reason)
        self.assertEqual("lead_planner", decision.source)

    def test_explicit_task_ids_dispatch_existing_tasks_not_generic_roster(self) -> None:
        from app.persistence import run_store, task_store
        from app.workspace_agents.lead_fan_out import materialize_lead_fan_out

        first_ui = task_store.create_task(
            workspace_id="workspace_dashpro",
            goal="Add previous-day navigation controls to the Practice at Home canary screen.",
            acceptance_criteria="Back arrow shows previous day poem content.",
            owner_role="frontend",
            allowed_paths=["apps", "components", "tests"],
        )
        backend = task_store.create_task(
            workspace_id="workspace_dashpro",
            goal="Add getTeacherSentAssignments(teacherId) to teacherDataService.ts.",
            acceptance_criteria="Function returns typed homework assignment rows.",
            owner_role="backend",
            allowed_paths=["lib", "services", "tests"],
        )
        second_ui = task_store.create_task(
            workspace_id="workspace_dashpro",
            goal="Build a Sent Activities history view in the teacher dashboard.",
            acceptance_criteria="Teacher can view and duplicate sent activities.",
            owner_role="frontend",
            dependencies=[str(backend["task_id"])],
            allowed_paths=["apps", "components", "tests"],
        )

        result = materialize_lead_fan_out(
            workspace_id="workspace_dashpro",
            goal=(
                "The three tasks from this morning are still open — "
                f"{first_ui['task_id']}, {second_ui['task_id']}, and {backend['task_id']} — "
                "they were never dispatched. Assign the two UI tasks to Priya "
                "(frontend) and the teacher query task to the backend specialist now. "
                "Use materialize_lead_fan_out with create_runs=True or directly lease "
                "those tasks and create queued runs."
            ),
            mode="fan_out",
            create_runs=True,
        )

        self.assertEqual("fan_out", result["mode"])
        self.assertEqual(
            {first_ui["task_id"], backend["task_id"], second_ui["task_id"]},
            {task["task_id"] for task in result["tasks"]},
        )
        self.assertEqual(
            {first_ui["task_id"], backend["task_id"]},
            {run["task_id"] for run in result["runs"]},
        )
        self.assertEqual(
            [second_ui["task_id"]],
            [row["task_id"] for row in result["deferred"]],
        )
        self.assertEqual("dependencies_incomplete", result["deferred"][0]["reason"])
        self.assertEqual(
            {"frontend", "backend"},
            {run["owner_role"] for run in result["runs"]},
        )
        self.assertNotIn("watcher", {run["owner_role"] for run in result["runs"]})
        self.assertNotIn("integrations", {run["owner_role"] for run in result["runs"]})
        for run in result["runs"]:
            stored = run_store.get_run(str(run["run_id"]))
            self.assertIsNotNone(stored)
            assert stored is not None
            self.assertEqual("queued", stored["phase"])
            self.assertEqual(run["task_id"], stored["task_id"])

        from app.persistence import chat_store

        priya_thread = chat_store.find_thread_for_employee(
            "workspace_dashpro",
            employee_id="employee-workspace_dashpro-frontend-2",
            thread_kind="ide",
        )
        self.assertIsNotNone(priya_thread)
        assert priya_thread is not None
        priya_messages = chat_store.list_thread_messages(str(priya_thread["thread_id"]))
        queued = [message for message in priya_messages if message.get("run_id")]
        self.assertTrue(queued)
        first_card = queued[0]
        self.assertEqual("agent", first_card.get("role"))
        self.assertEqual("Dana", first_card.get("speaker_name"))
        self.assertEqual("lead", first_card.get("speaker_role"))
        content = str(first_card.get("content") or "")
        self.assertIn("Dana queued a Frontend assignment for Priya.", content)
        self.assertIn("Assignment: Add previous-day navigation controls", content)
        self.assertIn("Receipt: task-", content)
        self.assertNotIn("Queued for dispatch ·", content)


if __name__ == "__main__":
    unittest.main()
