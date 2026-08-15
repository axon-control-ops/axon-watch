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
from app.workspace_agents import worker_dispatch  # noqa: E402
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
        with patch.object(
            worker_dispatch,
            "generate_lane_b_result",
            return_value={
                "dispatched": True,
                "runtime_label": "test",
                "content": "OTA command completed by terminal receipt.\n\nConfidence: 10/10",
            },
        ), patch.object(
            worker_dispatch,
            "resolve_worker_execution_policy",
            return_value=role_execution_policy("integrations"),
        ), patch.object(
            worker_dispatch,
            "prepare_worker_ide_stream",
            return_value=None,
        ), patch.object(
            worker_dispatch,
            "finalize_lane_b_agent_run",
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
        ), patch(
            "app.workspace_agents.lead_replan.notify_lead_after_worker_task",
            return_value=None,
        ):
            dispatched, finalized = worker_dispatch.dispatch_continuous_worker_run(
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

    def test_no_change_supabase_migration_fix_is_not_successful_delivery(self) -> None:
        task = {
            "owner_role": "backend",
            "goal": "Fix the Supabase migration SQL lint failure.",
            "acceptance_criteria": "Run SQLFluff lint on the changed migration and report the command output.",
            "allowed_paths": ["supabase", "scripts", "tests"],
        }

        self.assertFalse(no_change_delivery_is_successful_ops_task(task))

    def test_full_access_no_change_verification_task_completes_with_terminal_receipt(self) -> None:
        from app.terminal import agent_jobs

        opened = task_store.create_task(
            workspace_id="workspace_worker_verify_noop",
            goal=(
                "Verification after Marco (backend): run scoped verify commands — "
                "`npm test -- tests/unit/services/staffVisibility.test.ts` "
                "[from run run_demo]"
            ),
            owner_role="backend",
            acceptance_criteria="Attach stdout receipts.",
        )
        leased = task_store.lease_task(
            opened["task_id"],
            lease_holder="employee-workspace_worker_verify_noop-backend",
        )
        created = create_run(
            workspace_id="workspace_worker_verify_noop",
            mode="agent",
            summary="Backend verification shift",
            employee_role="backend",
            task_id=leased["task_id"],
            require_leased_task=True,
        )
        run_id = str(created["run_id"])
        with agent_jobs._lock:
            agent_jobs._jobs["agent-job-verify-noop"] = {
                "job_id": "agent-job-verify-noop",
                "workspace_id": "workspace_worker_verify_noop",
                "run_id": run_id,
                "command": "npm test -- tests/unit/services/staffVisibility.test.ts",
                "status": "completed",
                "exit_code": 0,
                "created_at": "2026-01-01T00:00:00Z",
            }
        with patch.object(
            worker_dispatch,
            "generate_lane_b_result",
            return_value={
                "dispatched": True,
                "runtime_label": "test",
                "content": "Tests passed with terminal stdout attached.\n\nConfidence: 10/10",
            },
        ), patch.object(
            worker_dispatch,
            "resolve_worker_execution_policy",
            return_value=role_execution_policy("backend"),
        ), patch.object(
            worker_dispatch,
            "prepare_worker_ide_stream",
            return_value=None,
        ), patch.object(
            worker_dispatch,
            "finalize_lane_b_agent_run",
            return_value=(True, {"phase": "executing"}),
        ), patch(
            "app.workspace_agents.verifier_contract.run_requires_acceptance_evidence",
            return_value=True,
        ), patch(
            "app.workspace_agents.verifier_contract.has_passing_acceptance_evidence",
            return_value=False,
        ), patch(
            "app.workspace_delivery.publish_worker_isolation",
            return_value=PublishResult(
                ok=True,
                stage="no_change",
                delivery={"delivery_id": "delivery-verify-noop"},
                detail="no changes",
                cleanup_isolation=True,
            ),
        ), patch(
            "app.workspace_agents.lead_replan.notify_lead_after_worker_task",
            return_value=None,
        ):
            dispatched, finalized = worker_dispatch.dispatch_continuous_worker_run(
                workspace_id="workspace_worker_verify_noop",
                employee=EmployeeConfig(
                    name="Marco",
                    role="backend",
                    owns="Backend",
                    schedule="continuous",
                ),
                run_record=created,
            )

        self.assertTrue(dispatched)
        self.assertIsNotNone(finalized)
        self.assertEqual("completed", finalized["phase"])  # type: ignore[index]
        task = task_store.get_task(leased["task_id"])
        self.assertEqual("completed", task["status"])  # type: ignore[index]
        history = run_store.list_history(get_run(run_id)["history_ref"])
        summaries = [
            str(item.get("receipt", {}).get("summary") or "").lower() for item in history
        ]
        self.assertTrue(
            any("verification shift required terminal job receipts" in summary for summary in summaries),
            summaries,
        )
        self.assertTrue(
            any("acceptance=pass" in summary for summary in summaries),
            summaries,
        )
