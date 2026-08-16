"""Every role must be told how to write files and how to declare receipts."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.cli_runtime.agent_shell_hook import evaluate_hook_payload  # noqa: E402
from app.workspace_agents.execution_policy import resolve_effective_policy  # noqa: E402

ROLES = ("lead", "backend", "frontend", "integrations", "watcher")


class WriteContractPromptTests(unittest.TestCase):
    def _prompt(self, role: str) -> str:
        from app.workspace_agents.config_loader import EmployeeConfig
        from app.workspace_agents.worker_prompt import build_continuous_worker_prompt

        return build_continuous_worker_prompt(
            workspace_id="workspace_dashpro",
            employee=EmployeeConfig(name="Probe", role=role, owns="probe"),
            task={"task_id": "task-probe", "goal": "Write a shift receipt"},
        )

    def test_every_role_is_told_not_to_write_via_an_interpreter(self) -> None:
        # The lead branch returns its own tools string rather than the shared
        # one, and the lead is the role that actually hit this in production.
        for role in ROLES:
            with self.subTest(role=role):
                self.assertIn("never a shell interpreter", self._prompt(role))

    def test_every_role_is_told_to_call_wrappers_directly(self) -> None:
        for role in ROLES:
            with self.subTest(role=role):
                prompt = self._prompt(role)
                self.assertIn("Never wrap one in", prompt)
                self.assertIn("route shell work through", prompt)
                self.assertIn("never that the tool does not exist", prompt)

    def test_every_role_is_told_to_name_the_exact_receipt_path(self) -> None:
        for role in ROLES:
            with self.subTest(role=role):
                prompt = self._prompt(role)
                self.assertIn("same directory and same extension", prompt)
                self.assertIn("docs/ops/agent-reports/", prompt)


class InterpreterWritesAreActuallyDeniedTests(unittest.TestCase):
    """The prompt claim must match what the hook really does."""

    def _permission(self, role: str, command: str) -> str:
        policy = resolve_effective_policy(
            role=role, workspace_allowed_paths=(), task_allowed_paths=None
        )
        return evaluate_hook_payload(
            {"hook_event_name": "beforeShellExecution", "command": command},
            approved_wrappers=frozenset(policy.approved_wrappers),
            approved_command_prefixes=policy.approved_command_prefixes,
        )["permission"]

    def test_wrapping_an_approved_wrapper_in_a_shell_is_denied(self) -> None:
        # Regression: a Lead ran zsh -lc "axon-assign ...", got denied, and
        # reported axon-assign as missing rather than as mis-invoked.
        self.assertEqual(
            "deny",
            self._permission("lead", '/usr/bin/zsh -lc "axon-assign --workspace w -- goal"'),
        )
        self.assertEqual(
            "allow", self._permission("lead", "axon-assign --workspace w -- goal")
        )

    def test_headless_form_reaches_the_full_frontend_toolchain(self) -> None:
        for command in (
            "npx jest tests/components/x.test.tsx",
            "npm test -- tests/components/x.test.tsx",
            "npx tsc --noEmit",
            "axon-agent-terminal-job --workspace w -- npx jest tests/components/x.test.tsx",
            "axon-agent-terminal-job --workspace w -- npx tsc --noEmit",
        ):
            with self.subTest(command=command):
                self.assertEqual("allow", self._permission("frontend", command))

    def test_interpreter_file_writes_are_denied_for_every_role(self) -> None:
        commands = (
            'node -e "require(\'fs\').writeFileSync(\'x\',\'y\')"',
            'python3 -c "open(\'x\',\'w\')"',
            "bash -c ls",
            "sh -c ls",
        )
        for role in ROLES:
            for command in commands:
                with self.subTest(role=role, command=command):
                    self.assertEqual("deny", self._permission(role, command))


if __name__ == "__main__":
    unittest.main()
