from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.terminal.agent_job_access import (  # noqa: E402
    AgentTerminalPolicyError,
    assert_agent_terminal_job_allowed,
)
from app.workspace_agents.execution_policy import role_execution_policy  # noqa: E402


class AgentTerminalPolicyTests(unittest.TestCase):
    def test_operator_call_does_not_claim_agent_identity(self) -> None:
        self.assertIsNone(
            assert_agent_terminal_job_allowed(
                workspace_id="workspace_demo",
                source_workspace_id=None,
                run_id=None,
                command="echo operator",
            )
        )

    def test_agent_requires_run_identity_and_same_workspace(self) -> None:
        with self.assertRaisesRegex(AgentTerminalPolicyError, "trusted run_id"):
            assert_agent_terminal_job_allowed(
                workspace_id="workspace_demo",
                source_workspace_id="workspace_demo",
                run_id=None,
                command="git status",
            )
        with self.assertRaisesRegex(AgentTerminalPolicyError, "another workspace"):
            assert_agent_terminal_job_allowed(
                workspace_id="workspace_other",
                source_workspace_id="workspace_demo",
                run_id="run_demo",
                command="git status",
            )

    @patch("app.terminal.agent_job_access.append_run_execution_receipt")
    @patch("app.terminal.agent_job_access.resolve_workspace_root")
    @patch("app.terminal.agent_job_access.task_store.get_task")
    @patch("app.terminal.agent_job_access.get_run")
    def test_integrations_lane_b_without_task_can_enqueue_ship_job(
        self,
        get_run,
        get_task,
        resolve_root,
        append_receipt,
    ) -> None:
        get_run.return_value = {
            "workspace_id": "workspace_dashpro",
            "employee_role": "integrations",
            "task_id": "",
        }
        get_task.return_value = None
        resolve_root.return_value = Path("/tmp/workspace_dashpro")

        role = assert_agent_terminal_job_allowed(
            workspace_id="workspace_dashpro",
            source_workspace_id="workspace_dashpro",
            run_id="run_direct_soren",
            command="npm run ota:canary",
        )

        self.assertEqual("integrations", role)
        append_receipt.assert_called()

    @patch("app.terminal.agent_job_access.append_run_execution_receipt")
    @patch("app.terminal.agent_job_access.resolve_workspace_root")
    @patch("app.terminal.agent_job_access.task_store.get_task")
    @patch("app.terminal.agent_job_access.get_run")
    def test_integrations_lane_b_without_task_still_gates_production_deploy(
        self,
        get_run,
        get_task,
        resolve_root,
        append_receipt,
    ) -> None:
        get_run.return_value = {
            "workspace_id": "workspace_dashpro",
            "employee_role": "integrations",
            "task_id": "",
        }
        get_task.return_value = None
        resolve_root.return_value = Path("/tmp/workspace_dashpro")

        with self.assertRaisesRegex(AgentTerminalPolicyError, "publication gate"):
            assert_agent_terminal_job_allowed(
                workspace_id="workspace_dashpro",
                source_workspace_id="workspace_dashpro",
                run_id="run_direct_soren",
                command="vercel deploy --prod --yes",
            )
        append_receipt.assert_called()

    @patch("app.terminal.agent_job_access.resolve_workspace_root")
    @patch("app.terminal.agent_job_access.task_store.get_task")
    @patch("app.terminal.agent_job_access.get_run")
    @patch("app.terminal.agent_job_access.append_run_execution_receipt")
    def test_no_task_full_role_can_run_normal_role_tools(
        self,
        append_receipt,
        get_run,
        get_task,
        resolve_root,
    ) -> None:
        get_run.return_value = {
            "workspace_id": "workspace_dashpro",
            "employee_role": "integrations",
            "task_id": "",
        }
        get_task.return_value = None
        resolve_root.return_value = Path("/tmp/workspace_dashpro")

        role = assert_agent_terminal_job_allowed(
            workspace_id="workspace_dashpro",
            source_workspace_id="workspace_dashpro",
            run_id="run_direct_soren",
            command="npm install",
        )
        self.assertEqual("integrations", role)
        append_receipt.assert_called_once()

    @patch("app.terminal.agent_job_access.append_run_execution_receipt")
    @patch("app.terminal.agent_job_access.resolve_worker_execution_policy")
    @patch("app.terminal.agent_job_access.resolve_workspace_root")
    @patch("app.terminal.agent_job_access.task_store.get_task")
    @patch("app.terminal.agent_job_access.get_run")
    def test_scoped_agent_command_is_checked_against_effective_policy(
        self,
        get_run,
        get_task,
        resolve_root,
        resolve_policy,
        append_receipt,
    ) -> None:
        get_run.return_value = {
            "workspace_id": "workspace_demo",
            "employee_role": "watcher",
            "task_id": "task_demo",
        }
        get_task.return_value = {"task_id": "task_demo", "allowed_paths": ["tests"]}
        resolve_root.return_value = Path("/tmp/workspace_demo")
        resolve_policy.return_value = role_execution_policy("watcher")

        role = assert_agent_terminal_job_allowed(
            workspace_id="workspace_demo",
            source_workspace_id="workspace_demo",
            run_id="run_demo",
            command="git status --short",
        )
        self.assertEqual("watcher", role)
        self.assertTrue(append_receipt.called)

        role = assert_agent_terminal_job_allowed(
            workspace_id="workspace_demo",
            source_workspace_id="workspace_demo",
            run_id="run_demo",
            command="curl https://example.invalid",
        )
        self.assertEqual("watcher", role)

    @patch("app.terminal.agent_job_access.append_run_execution_receipt")
    @patch("app.terminal.agent_job_access.resolve_worker_execution_policy")
    @patch("app.terminal.agent_job_access.resolve_workspace_root")
    @patch("app.terminal.agent_job_access.run_store.save_run")
    @patch("app.terminal.agent_job_access.task_store.bind_task_run")
    @patch("app.terminal.agent_job_access.task_store.lease_task")
    @patch("app.terminal.agent_job_access.task_store.get_task")
    @patch("app.terminal.agent_job_access.task_store.list_tasks")
    @patch("app.terminal.agent_job_access.get_run")
    def test_backend_run_without_task_id_can_use_open_verification_task(
        self,
        get_run,
        list_tasks,
        get_task,
        lease_task,
        bind_task_run,
        save_run,
        resolve_root,
        resolve_policy,
        append_receipt,
    ) -> None:
        get_run.return_value = {
            "run_id": "run_marco_verify",
            "workspace_id": "workspace_dashpro",
            "employee_role": "backend",
            "task_id": "",
        }
        list_tasks.return_value = [
            {
                "task_id": "task_verify",
                "workspace_id": "workspace_dashpro",
                "owner_role": "backend",
                "status": "open",
                "goal": "Verification after Marco (backend): run scoped verify commands",
                "updated_at": "2026-08-13T12:00:00Z",
                "allowed_paths": ["tests", "services"],
            }
        ]
        leased = {
            "task_id": "task_verify",
            "status": "leased",
            "owner_role": "backend",
            "allowed_paths": ["tests", "services"],
        }
        lease_task.return_value = leased
        get_task.side_effect = lambda task_id: leased if task_id == "task_verify" else None
        save_run.side_effect = lambda record: record
        bind_task_run.return_value = leased
        resolve_root.return_value = Path("/tmp/workspace_dashpro")
        resolve_policy.return_value = role_execution_policy("backend")

        role = assert_agent_terminal_job_allowed(
            workspace_id="workspace_dashpro",
            source_workspace_id="workspace_dashpro",
            run_id="run_marco_verify",
            command="axon-agent-terminal-job -- npm test -- tests/unit/services/staffVisibility.test.ts",
        )

        self.assertEqual("backend", role)
        lease_task.assert_called_once()
        save_run.assert_called()
        append_receipt.assert_called()


if __name__ == "__main__":
    unittest.main()
