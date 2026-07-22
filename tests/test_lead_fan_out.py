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
        from app.persistence import run_store

        isolate_control_plane_db(self, run_store)

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
            history = run_store.list_history(stored["history_ref"])
            types = [
                str(item.get("receipt", {}).get("type") or "") for item in history
            ]
            self.assertIn("lead_fan_out_assigned", types)
            task = task_store.get_task(str(run["task_id"]))
            self.assertIsNotNone(task)
            assert task is not None
            self.assertEqual("leased", task["status"])

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


if __name__ == "__main__":
    unittest.main()
