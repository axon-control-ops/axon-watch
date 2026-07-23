"""Continuous worker → specialist IDE thread streaming."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.persistence import chat_store, run_store, task_store  # noqa: E402
from app.runs.service import create_run  # noqa: E402
from app.workspace_agents.config_loader import EmployeeConfig  # noqa: E402


def _seed_leased_run(*, workspace_id: str, owner_role: str, goal: str) -> dict[str, object]:
    opened = task_store.create_task(
        workspace_id=workspace_id,
        owner_role=owner_role,
        goal=goal,
        acceptance_criteria="receipts prove the goal",
    )
    leased = task_store.lease_task(
        opened["task_id"],
        lease_holder=f"employee-{workspace_id}-{owner_role}",
    )
    return create_run(
        workspace_id=workspace_id,
        mode="agent",
        summary=f"{owner_role} continuous shift",
        employee_role=owner_role,
        task_id=leased["task_id"],
        require_leased_task=True,
    )


class WorkerIdeStreamTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)
        chat_store.reset_store()
        task_store.reset_store()
        self.addCleanup(chat_store.reset_store)
        self.addCleanup(task_store.reset_store)

    def test_dispatch_mirrors_lane_b_into_employee_ide_thread(self) -> None:
        from app.workspace_agents.worker_dispatch import dispatch_continuous_worker_run

        workspace_id = "workspace_worker_ide"
        employee_id = "employee-workspace_worker_ide-backend-0"
        created = _seed_leased_run(
            workspace_id=workspace_id,
            owner_role="backend",
            goal="Ship IDE mirror for continuous workers",
        )
        run_id = str(created["run_id"])
        isolation = Path(tempfile.mkdtemp(prefix="axon-worker-ide-"))

        def fake_lane_b(**kwargs: object) -> dict[str, object]:
            on_chunk = kwargs.get("on_chunk")
            assert callable(on_chunk)
            on_chunk("partial answer", "partial answer")
            on_chunk(
                "final answer\n\nCritical Review Confidence: 9/10",
                "\n\nCritical Review Confidence: 9/10",
            )
            return {
                "dispatched": True,
                "runtime_label": "test",
                "content": "final answer\n\nCritical Review Confidence: 9/10",
            }

        with patch(
            "app.workspace_agents.worker_dispatch.generate_lane_b_result",
            side_effect=fake_lane_b,
        ), patch(
            "app.workspace_agents.worker_dispatch.create_worker_isolation",
            return_value=isolation,
        ), patch(
            "app.workspace_agents.worker_dispatch.worker_agent_workspace",
            return_value=isolation,
        ), patch(
            "app.workspace_agents.worker_dispatch.cleanup_worker_isolation",
            return_value={"cleaned": True, "removed": True},
        ):
            dispatched, finalized = dispatch_continuous_worker_run(
                workspace_id=workspace_id,
                employee=EmployeeConfig(
                    name="API Craft",
                    role="backend",
                    owns="APIs",
                    schedule="continuous",
                    employee_id=employee_id,
                ),
                run_record=created,
            )

        self.assertTrue(dispatched)
        assert finalized is not None
        self.assertEqual("completed", finalized["phase"])

        thread = chat_store.find_thread_for_employee(
            workspace_id,
            employee_id=employee_id,
            thread_kind="ide",
        )
        assert thread is not None
        self.assertEqual(run_id, thread.get("run_id"))
        messages = chat_store.list_thread_messages(str(thread["thread_id"]))
        roles = [str(item.get("role") or "") for item in messages]
        self.assertIn("operator", roles)
        self.assertIn("system", roles)
        self.assertIn("agent", roles)
        agent = next(item for item in messages if item.get("role") == "agent")
        self.assertIn("Critical Review Confidence: 9/10", str(agent.get("content") or ""))
        self.assertIn(run_id, str(agent.get("run_id") or ""))

    def test_dispatch_crash_posts_error_into_employee_thread(self) -> None:
        from app.workspace_agents.worker_dispatch import dispatch_continuous_worker_run

        workspace_id = "workspace_worker_ide_fail"
        employee_id = "employee-workspace_worker_ide_fail-watcher-0"
        created = _seed_leased_run(
            workspace_id=workspace_id,
            owner_role="watcher",
            goal="Surface crash in IDE",
        )

        with patch(
            "app.workspace_agents.worker_dispatch.generate_lane_b_result",
            side_effect=RuntimeError("boom"),
        ), patch(
            "app.workspace_agents.worker_dispatch.create_worker_isolation",
            return_value=__import__("pathlib").Path("/tmp/axon-worker-ide-fail/checkout"),
        ), patch(
            "app.workspace_agents.worker_dispatch.worker_agent_workspace",
            return_value=__import__("pathlib").Path("/tmp/axon-worker-ide-fail/checkout"),
        ), patch(
            "app.workspace_agents.worker_dispatch.cleanup_worker_isolation",
            return_value={"cleaned": True, "removed": True},
        ):
            dispatched, finalized = dispatch_continuous_worker_run(
                workspace_id=workspace_id,
                employee=EmployeeConfig(
                    name="Cass",
                    role="watcher",
                    owns="Sentry",
                    schedule="continuous",
                    employee_id=employee_id,
                ),
                run_record=created,
            )

        self.assertFalse(dispatched)
        assert finalized is not None
        self.assertEqual("failed", finalized["phase"])
        thread = chat_store.find_thread_for_employee(
            workspace_id,
            employee_id=employee_id,
            thread_kind="ide",
        )
        assert thread is not None
        messages = chat_store.list_thread_messages(str(thread["thread_id"]))
        agent = next(item for item in messages if item.get("role") == "agent")
        self.assertIn("boom", str(agent.get("content") or ""))


if __name__ == "__main__":
    unittest.main()
