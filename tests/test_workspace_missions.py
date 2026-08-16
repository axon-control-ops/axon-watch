"""Durable cross-workspace mission planning and gate coverage."""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.persistence import handoff_store, task_store, workspace_mission_store
from app.workspace_delivery import store as delivery_store
from app.workspace_missions import impact_graph, service


class WorkspaceMissionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.previous_db = os.environ.get("AXON_WATCH_CONTROL_PLANE_DB")
        self.previous_config = os.environ.get("AXON_WORKSPACE_DEPENDENCIES_FILE")
        os.environ["AXON_WATCH_CONTROL_PLANE_DB"] = str(base / "control.sqlite3")
        self.config = base / "dependencies.json"
        os.environ["AXON_WORKSPACE_DEPENDENCIES_FILE"] = str(self.config)
        task_store.reset_store()
        handoff_store.reset_store()
        workspace_mission_store.reset_store()
        delivery_store.reset_store_for_tests()
        self.addCleanup(self._restore_env)

    def _restore_env(self) -> None:
        for name, value in (
            ("AXON_WATCH_CONTROL_PLANE_DB", self.previous_db),
            ("AXON_WORKSPACE_DEPENDENCIES_FILE", self.previous_config),
        ):
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value

    def _write_edges(self, edges: list[dict]) -> None:
        self.config.write_text(json.dumps({"version": 1, "edges": edges}), encoding="utf-8")

    @staticmethod
    def _records():
        return [
            {"workspace_id": "source", "project_root": "/tmp/source"},
            {"workspace_id": "consumer", "project_root": "/tmp/consumer"},
        ]

    def test_explicit_edge_creates_idempotent_dependent_tasks_and_handoff(self) -> None:
        self._write_edges([{
            "source_workspace_id": "source", "target_workspace_id": "consumer",
            "verification_commands": ["npm test"], "promotion_order": 2,
        }])
        with (
            patch.object(impact_graph, "list_workspace_records", return_value=self._records()),
            patch.object(service, "_route_role", return_value="backend"),
            patch("app.workspace_handoff_routing.try_autostart_handoff_task"),
        ):
            first = service.create_workspace_mission(source_workspace_id="source", goal="Change shared API")
            second = service.create_workspace_mission(source_workspace_id="source", goal="Change shared API")
        self.assertEqual(first["mission_id"], second["mission_id"])
        self.assertEqual(len(first["nodes"]), 2)
        source_node, target_node = first["nodes"]
        self.assertEqual(target_node["dependency_task_ids"], [source_node["task_id"]])
        self.assertEqual(task_store.get_task(target_node["task_id"])["mission_id"], first["mission_id"])
        handoffs = handoff_store.list_recent_handoffs(limit=10)
        self.assertEqual(handoffs[0]["mission_id"], first["mission_id"])

    def test_missing_target_and_cycle_require_lead_review(self) -> None:
        self._write_edges([
            {"source_workspace_id": "source", "target_workspace_id": "consumer"},
            {"source_workspace_id": "consumer", "target_workspace_id": "source"},
            {"source_workspace_id": "source", "target_workspace_id": "missing"},
        ])
        with patch.object(impact_graph, "list_workspace_records", return_value=self._records()):
            preview = service.preview_workspace_impact("source", "change")
        self.assertEqual(preview["actionable_count"], 0)
        self.assertEqual(preview["review_count"], 2)
        self.assertTrue(all(edge["review_reason"] for edge in preview["edges"]))

    def test_verification_waits_for_green_delivery(self) -> None:
        self._write_edges([])
        task = task_store.create_task(workspace_id="source", goal="source", mission_id="pending")
        task_store.lease_task(task["task_id"], lease_holder="test")
        task_store.complete_task(task["task_id"], run_id="run-1")
        mission = workspace_mission_store.create_mission({
            "mission_id": "pending", "dedupe_key": "pending", "goal": "source",
            "status": "verifying", "risk": "normal", "source_workspace_id": "source",
        })
        workspace_mission_store.create_node({
            "node_id": "node-pending", "mission_id": "pending", "workspace_id": "source",
            "task_id": task["task_id"], "relation": "source", "status": "completed",
        })
        delivery_store.create_delivery(
            workspace_id="source", run_id="run-1", task_id=task["task_id"],
            stage="ci_pending", baseline_sha="base", worker_branch="worker/run-1",
        )
        result = service.verify_mission(str(mission["mission_id"]))
        self.assertEqual(result["status"], "verifying")
        self.assertIn("waiting for green", result["blocker"])

    def test_ready_for_promotion_is_not_downgraded_by_read(self) -> None:
        mission = workspace_mission_store.create_mission({
            "mission_id": "ready", "dedupe_key": "ready", "goal": "ready",
            "status": "ready_for_promotion", "risk": "normal", "source_workspace_id": "source",
        })
        task = task_store.create_task(workspace_id="source", goal="ready", mission_id="ready")
        task_store.lease_task(task["task_id"], lease_holder="test")
        task_store.complete_task(task["task_id"])
        workspace_mission_store.create_node({
            "node_id": "node-ready", "mission_id": mission["mission_id"],
            "workspace_id": "source", "task_id": task["task_id"],
            "relation": "source", "status": "completed",
        })
        self.assertEqual(service.get_workspace_mission("ready")["status"], "ready_for_promotion")


if __name__ == "__main__":
    unittest.main()
