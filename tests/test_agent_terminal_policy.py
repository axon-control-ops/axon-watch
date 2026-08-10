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

    @patch("app.terminal.agent_job_access.resolve_workspace_root")
    @patch("app.terminal.agent_job_access.task_store.get_task")
    @patch("app.terminal.agent_job_access.get_run")
    def test_no_task_agent_terminal_still_denies_non_ship_commands(
        self,
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

        with self.assertRaisesRegex(AgentTerminalPolicyError, "no scoped task"):
            assert_agent_terminal_job_allowed(
                workspace_id="workspace_dashpro",
                source_workspace_id="workspace_dashpro",
                run_id="run_direct_soren",
                command="npm install",
            )

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

        with self.assertRaises(AgentTerminalPolicyError):
            assert_agent_terminal_job_allowed(
                workspace_id="workspace_demo",
                source_workspace_id="workspace_demo",
                run_id="run_demo",
                command="curl https://example.invalid",
            )


if __name__ == "__main__":
    unittest.main()
