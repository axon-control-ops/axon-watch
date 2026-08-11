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
from app.workspace_agents.ops_delivery import no_change_delivery_is_successful_ops_task  # noqa: E402
from app.workspace_agents.worker_dispatch import dispatch_continuous_worker_run  # noqa: E402
from app.workspace_delivery.publish import PublishResult  # noqa: E402


class WorkerOpsDeliveryTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)
        task_store.reset_store()
        self.addCleanup(task_store.reset_store)

    def test_full_access_no_change_ops_task_completes_with_receipt(self) -> None:
        opened = task_store.create_task(
            workspace_id="workspace_worker_ops_noop",
            goal=(
                "Run the command `axon-agent-terminal-job --workspace workspace_dashpro "
                "-- npm run ota:canary` and report the Expo update receipt. "
                "Terminal job receipt proves the OTA publish; no code diff is expected."
            ),
            owner_role="integrations",
            acceptance_criteria="receipts prove the goal",
        )
        leased = task_store.lease_task(
            opened["task_id"],
            lease_holder="employee-workspace_worker_ops_noop-integrations",
        )
        created = create_run(
            workspace_id="workspace_worker_ops_noop",
            mode="agent",
            summary="Integrations ops shift",
            employee_role="integrations",
            task_id=leased["task_id"],
            require_leased_task=True,
        )
        with patch(
            "app.workspace_agents.worker_dispatch.generate_lane_b_result",
            return_value={
                "dispatched": True,
                "runtime_label": "test",
                "content": "OTA command completed by terminal receipt.\n\nConfidence: 10/10",
            },
        ), patch(
            "app.workspace_agents.worker_dispatch.resolve_worker_execution_policy",
            return_value=role_execution_policy("integrations"),
        ), patch(
            "app.workspace_agents.worker_dispatch.finalize_lane_b_agent_run",
            return_value=(True, {"phase": "executing"}),
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
                delivery={"delivery_id": "delivery-ops-noop"},
                detail="no changes",
                cleanup_isolation=True,
            ),
        ):
            dispatched, finalized = dispatch_continuous_worker_run(
                workspace_id="workspace_worker_ops_noop",
                employee=EmployeeConfig(
                    name="Release Ops",
                    role="integrations",
                    owns="OTA publish",
                    schedule="continuous",
                ),
                run_record=created,
            )

        self.assertTrue(dispatched)
        self.assertIsNotNone(finalized)
        self.assertEqual("completed", finalized["phase"])  # type: ignore[index]
        task = task_store.get_task(leased["task_id"])
        self.assertEqual("completed", task["status"])  # type: ignore[index]
        history = run_store.list_history(get_run(str(created["run_id"]))["history_ref"])
        summaries = [str(item.get("receipt", {}).get("summary") or "").lower() for item in history]
        self.assertTrue(any("receipt-backed ops/coordination task" in summary for summary in summaries), summaries)

    def test_no_change_lead_plan_coordination_task_is_successful_delivery(self) -> None:
        task = {
            "owner_role": "lead",
            "goal": (
                'Lead: advance "Continue the interrupted run" toward Done '
                "[plan lead-plan-98e0c2101c784265] — after Priya (frontend) completed."
            ),
            "acceptance_criteria": (
                "Sole truth: advance plan lead-plan-98e0c2101c784265. "
                "Decide whether to assign a specialist, escalate Decide, or report receipts."
            ),
        }

        self.assertTrue(no_change_delivery_is_successful_ops_task(task))

    def test_no_change_regular_implementation_task_is_not_successful_delivery(self) -> None:
        task = {
            "owner_role": "frontend",
            "goal": "Fix the Student Management header UI.",
            "acceptance_criteria": "Code changes and visual verification required.",
        }

        self.assertFalse(no_change_delivery_is_successful_ops_task(task))
