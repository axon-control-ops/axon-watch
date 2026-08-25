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

    def test_every_role_is_told_it_has_full_tools_in_its_professional_lane(self) -> None:
        for role in ROLES:
            with self.subTest(role=role):
                prompt = self._prompt(role)
                self.assertIn("contract-bounded write surface for your professional role", prompt)
                self.assertIn("Full Access also permits project runtimes", prompt)
                self.assertIn("assign it directly to that colleague", prompt)

    def test_every_role_is_told_to_call_wrappers_directly(self) -> None:
        for role in ROLES:
            with self.subTest(role=role):
                prompt = self._prompt(role)
                self.assertIn("Direct invocation is preferred", prompt)
                self.assertIn("route shell work through", prompt)
                self.assertIn("does not prove that the tool is absent", prompt)

    def test_every_role_is_told_to_name_the_exact_receipt_path(self) -> None:
        for role in ROLES:
            with self.subTest(role=role):
                prompt = self._prompt(role)
                self.assertIn("same directory and same extension", prompt)
                self.assertIn("docs/ops/agent-reports/", prompt)


class FullRoleToolchainTests(unittest.TestCase):
    """The prompt claim must match what the hook really does."""

    def _permission(self, role: str, command: str) -> str:
        policy = resolve_effective_policy(
            role=role, workspace_allowed_paths=(".",), task_allowed_paths=None
        )
        return evaluate_hook_payload(
            {"hook_event_name": "beforeShellExecution", "command": command},
            approved_wrappers=frozenset(policy.approved_wrappers),
            approved_command_prefixes=policy.approved_command_prefixes,
            allow_all_tools=policy.allow_all_tools,
        )["permission"]

    def test_full_access_allows_shell_runtimes(self) -> None:
        self.assertEqual(
            "allow",
            self._permission("lead", '/usr/bin/zsh -lc "axon-assign --workspace w -- goal"'),
        )
        self.assertEqual(
            "allow", self._permission("lead", "axon-assign --workspace w -- goal")
        )

    def test_headless_form_reaches_the_full_frontend_toolchain(self) -> None:
        for command in (
            "npx --no-install jest tests/components/x.test.tsx",
            "npm test -- tests/components/x.test.tsx",
            "npx --no-install tsc --noEmit",
            "axon-agent-terminal-job --workspace w -- npx --no-install jest tests/components/x.test.tsx",
            "axon-agent-terminal-job --workspace w -- npx --no-install tsc --noEmit",
        ):
            with self.subTest(command=command):
                self.assertEqual("allow", self._permission("frontend", command))

    def test_interpreter_tools_are_available_for_every_role(self) -> None:
        commands = (
            'node -e "require(\'fs\').writeFileSync(\'x\',\'y\')"',
            'python3 -c "open(\'x\',\'w\')"',
            "bash -c ls",
            "sh -c ls",
        )
        for role in ROLES:
            for command in commands:
                with self.subTest(role=role, command=command):
                    self.assertEqual("allow", self._permission(role, command))


if __name__ == "__main__":
    unittest.main()
