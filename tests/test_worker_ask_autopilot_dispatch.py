from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.persistence import run_store, task_store  # noqa: E402
from app.runs.service import create_run, get_run  # noqa: E402
from app.workspace_agents.config_loader import EmployeeConfig  # noqa: E402
from app.workspace_agents.execution_policy import role_execution_policy  # noqa: E402
from app.workspace_agents.worker_dispatch import dispatch_continuous_worker_run  # noqa: E402
from app.workspace_delivery.publish import PublishResult  # noqa: E402


def _seed_open_task() -> dict:
    return task_store.create_task(
        workspace_id="workspace_worker_auto_ask",
        owner_role="frontend",
        goal="Fix the dashboard display bug",
        acceptance_criteria="receipts prove the goal",
    )


class WorkerAskAutopilotDispatchTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)
        task_store.reset_store()
        self.addCleanup(task_store.reset_store)

    def test_safe_ask_no_change_reopens_with_selected_answer_receipt(self) -> None:
        opened = _seed_open_task()
        leased = task_store.lease_task(
            opened["task_id"],
            lease_holder="employee-workspace_worker_auto_ask-frontend",
        )
        created = create_run(
            workspace_id="workspace_worker_auto_ask",
            mode="agent",
            summary="Frontend continuous shift",
            employee_role="frontend",
            task_id=leased["task_id"],
            require_leased_task=True,
        )
        run_id = str(created["run_id"])
        ask_reply = """
I found a likely stale dashboard route and need to continue safely.

:::ask Which continuation should I take?
- 1 | Specific change/PR unknown — need intended UI change
- 2 | Unsure — harden Fast Refresh reliability on teacher dashboard re-export barrel as precaution
:::

Confidence: 9/10
"""
        with patch(
            "app.workspace_agents.worker_dispatch.generate_lane_b_result",
            return_value={
                "dispatched": True,
                "runtime_label": "test",
                "content": ask_reply,
            },
        ), patch(
            "app.workspace_agents.worker_dispatch.resolve_worker_execution_policy",
            return_value=role_execution_policy("frontend"),
        ), patch(
            "app.workspace_agents.worker_dispatch.finalize_lane_b_agent_run",
            return_value=(True, {"phase": "executing"}),
        ), patch(
            "app.workspace_agents.worker_dispatch.worker_scheduler_settings_store.load_settings",
            return_value={"scheduler_enabled": True},
        ), patch(
            "app.workspace_agents.verifier_contract.run_requires_acceptance_evidence",
            return_value=True,
        ), patch(
            "app.workspace_agents.verifier_contract.has_passing_acceptance_evidence",
            return_value=True,
        ), patch(
            "app.workspace_delivery.publish_worker_isolation",
            return_value=PublishResult(
                ok=True,
                stage="no_change",
                delivery={"delivery_id": "delivery-auto-ask"},
                detail="no changes",
                cleanup_isolation=True,
            ),
        ):
            dispatched, finalized = dispatch_continuous_worker_run(
                workspace_id="workspace_worker_auto_ask",
                employee=EmployeeConfig(
                    name="Priya",
                    role="frontend",
                    owns="UI",
                    schedule="continuous",
                ),
                run_record=created,
            )

        self.assertFalse(dispatched)
        assert finalized is not None
        self.assertEqual("failed", finalized["phase"])
        task = task_store.get_task(leased["task_id"])
        assert task is not None
        self.assertEqual("open", task["status"])
        summaries = [
            str(item.get("receipt", {}).get("summary") or "")
            for item in run_store.list_history(get_run(run_id)["history_ref"])
        ]
        self.assertTrue(
            any("Auto mode resolved safe ask card" in summary for summary in summaries),
            summaries,
        )
        self.assertTrue(any("Selected option 2" in summary for summary in summaries), summaries)


if __name__ == "__main__":
    unittest.main()
