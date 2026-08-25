from __future__ import annotations

import json
import sys
import tempfile
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import patch


CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.workspace_agents.config_loader import (  # noqa: E402
    EmployeeConfig,
    WorkspaceAgentError,
    load_workspace_agent_configs,
)
from app.workspace_agents.execution_policy import (  # noqa: E402
    AgentExecutionPolicyOverride,
    resolve_effective_policy,
    role_execution_policy,
)
from app.workspace_agents.execution_policy_runtime import (  # noqa: E402
    resolve_worker_execution_policy,
)
from app.workspace_agents.execution_policy_prefixes import COMMON_READ_PREFIXES, VALIDATION_PREFIXES  # noqa: E402


class RoleExecutionPolicyTests(unittest.TestCase):
    def test_git_grep_is_approved_read_prefix(self) -> None:
        self.assertIn(("git", "grep"), COMMON_READ_PREFIXES)

    def test_mobile_companion_commands_are_narrowly_approved(self) -> None:
        self.assertIn(("npm", "run", "dev:console-mobile"), VALIDATION_PREFIXES)
        self.assertIn(
            ("npm", "exec", "-w", "@axon-watch/console-mobile", "--", "expo", "config", "--json"),
            VALIDATION_PREFIXES,
        )
        self.assertNotIn(("npm", "run", "dev"), VALIDATION_PREFIXES)

    def test_every_role_has_full_tools_and_a_role_owned_write_surface(self) -> None:
        roles = ("lead", "watcher", "frontend", "backend", "integrations")
        policies = [role_execution_policy(role) for role in roles]
        self.assertTrue(all(policy.read_paths == (".",) for policy in policies))
        self.assertTrue(all(policy.write_paths for policy in policies))
        self.assertTrue(all(policy.write_paths != (".",) for policy in policies))
        self.assertTrue(all(policy.execution_access == "full" for policy in policies))
        self.assertTrue(all(policy.allow_all_tools for policy in policies))
        self.assertTrue(all(policy.network_mode == "unrestricted" for policy in policies))
        self.assertTrue(all("axon-assign" in policy.approved_wrappers for policy in policies))
        self.assertIn("services", role_execution_policy("backend").write_paths)
        self.assertNotIn("apps", role_execution_policy("backend").write_paths)
        self.assertIn("apps", role_execution_policy("frontend").write_paths)
        self.assertNotIn("services", role_execution_policy("frontend").write_paths)
        self.assertTrue(
            all(policy.trust_policy == "worker" for policy in policies)
        )
        with self.assertRaises(FrozenInstanceError):
            policies[0].timeout_seconds = 1  # type: ignore[misc]

    def test_unknown_role_fails_closed(self) -> None:
        policy = role_execution_policy("custom")
        self.assertEqual((), policy.write_paths)
        self.assertEqual("consultative", policy.execution_access)
        self.assertEqual("none", policy.network_mode)


class EffectiveExecutionPolicyTests(unittest.TestCase):
    def test_task_is_a_hint_but_employee_and_contract_restrictions_win(self) -> None:
        override = AgentExecutionPolicyOverride(
            read_paths=("services",),
            write_paths=(),
            network_mode="none",
            execution_access="consultative",
            forbidden_path_globs=("**/.env",),
        )
        policy = resolve_effective_policy(
            role="backend",
            employee_override=override,
            workspace_allowed_paths=("apps",),
            workspace_forbidden_path_globs=("**/.env",),
            task_allowed_paths=("services",),
        )
        self.assertEqual(("services",), policy.read_paths)
        self.assertEqual((), policy.write_paths)
        self.assertNotIn("apps", policy.write_paths)
        self.assertIn("**/.env", policy.forbidden_path_globs)
        self.assertEqual("consultative", policy.execution_access)
        self.assertEqual("none", policy.network_mode)
        self.assertFalse(policy.allow_all_tools)

    def test_worker_boundary_keeps_full_access_for_legacy_empty_scope(self) -> None:
        employee = EmployeeConfig(role="backend")
        with patch(
            "app.workspace_agents.execution_policy_runtime.load_repo_contract",
            return_value={"allowed_paths": ["services", "tests"]},
        ):
            policy = resolve_worker_execution_policy(
                employee=employee,
                task_payload={"allowed_paths": []},
                workspace_root=Path("/workspace"),
            )

        self.assertEqual(("services", "tests"), policy.write_paths)
        self.assertEqual("full", policy.execution_access)
        self.assertTrue(policy.allow_all_tools)

    def test_frontend_task_hint_does_not_remove_command_centre_scope(self) -> None:
        policy = resolve_effective_policy(
            role="frontend",
            workspace_allowed_paths=("command-centre/", "components/", "docs/ops/"),
            task_allowed_paths=("components/",),
        )
        self.assertIn("command-centre", policy.write_paths)
        self.assertIn("components", policy.write_paths)
        self.assertEqual("full", policy.execution_access)

    def test_missing_project_contract_fails_closed_for_write_mounts(self) -> None:
        policy = resolve_effective_policy(
            role="backend",
            workspace_allowed_paths=(),
            task_allowed_paths=("services",),
        )
        self.assertEqual((), policy.write_paths)

    def test_explicit_employee_tool_restrictions_are_not_bypassed(self) -> None:
        from app.cli_runtime.agent_shell_hook import evaluate_hook_payload

        policy = resolve_effective_policy(
            role="backend",
            employee_override=AgentExecutionPolicyOverride(
                approved_wrapper_names=("run_contract_unit_tests.sh",),
                network_mode="none",
            ),
            workspace_allowed_paths=("services", "tests"),
            task_allowed_paths=None,
        )
        self.assertFalse(policy.allow_all_tools)
        decision = evaluate_hook_payload(
            {
                "hook_event_name": "beforeShellExecution",
                "command": "curl https://example.invalid",
            },
            approved_wrappers=frozenset(policy.approved_wrappers),
            approved_command_prefixes=policy.approved_command_prefixes,
            allow_all_tools=policy.allow_all_tools,
        )
        self.assertEqual("deny", decision["permission"])

    def test_operations_contract_adds_only_role_owned_paths(self) -> None:
        contract = (
            "command-centre/",
            "data/live/",
            "data/exports/",
            "docs/ops/",
            "scripts/",
        )
        backend = resolve_effective_policy(
            role="backend",
            workspace_allowed_paths=contract,
            task_allowed_paths=None,
        )
        frontend = resolve_effective_policy(
            role="frontend",
            workspace_allowed_paths=contract,
            task_allowed_paths=None,
        )
        integrations = resolve_effective_policy(
            role="integrations",
            workspace_allowed_paths=contract,
            task_allowed_paths=None,
        )
        self.assertIn("data/live", backend.write_paths)
        self.assertNotIn("data/exports", backend.write_paths)
        self.assertIn("command-centre", frontend.write_paths)
        self.assertNotIn("data/live", frontend.write_paths)
        self.assertIn("data/exports", integrations.write_paths)


class EmployeeExecutionPolicyConfigTests(unittest.TestCase):
    def test_employee_policy_override_parses_from_json(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            agents_file = Path(tempdir) / "agents.json"
            agents_file.write_text(
                json.dumps(
                    {
                        "companies": {
                            "workspace_demo": {
                                "employees": [
                                    {
                                        "name": "Reed",
                                        "role": "backend",
                                        "execution_policy": {
                                            "read_paths": ["services/"],
                                            "write_paths": [],
                                            "approved_wrappers": [
                                                "run_contract_unit_tests.sh"
                                            ],
                                            "command_prefixes": [
                                                "git status",
                                                ["git", "diff"],
                                            ],
                                            "capabilities": ["test"],
                                            "network_mode": "none",
                                            "timeout_seconds": 300,
                                            "trust_policy": "worker",
                                            "execution_access": "consultative",
                                        },
                                    }
                                ]
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            _configs, _defaults, companies, _staffing = load_workspace_agent_configs(
                agents_file
            )

        override = companies["workspace_demo"].employees[0].execution_policy
        self.assertIsNotNone(override)
        assert override is not None
        self.assertEqual(("services",), override.read_paths)
        self.assertEqual((), override.write_paths)
        self.assertEqual(
            (("git", "status"), ("git", "diff")),
            override.approved_command_prefixes,
        )
        self.assertEqual(300, override.timeout_seconds)

    def test_invalid_employee_policy_rejects_the_config(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            agents_file = Path(tempdir) / "agents.json"
            agents_file.write_text(
                json.dumps(
                    {
                        "companies": {
                            "workspace_demo": {
                                "employees": [
                                    {
                                        "role": "backend",
                                        "execution_policy": {
                                            "network_mode": "allow_everything"
                                        },
                                    }
                                ]
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                WorkspaceAgentError, "invalid employee execution_policy"
            ):
                load_workspace_agent_configs(agents_file)


class SelfValidationPolicyTests(unittest.TestCase):
    """The completion gate demands test evidence; the sandbox must permit it."""

    def _policy(self, role: str):
        from app.workspace_agents.execution_policy import resolve_effective_policy

        return resolve_effective_policy(
            role=role,
            workspace_allowed_paths=(".",),
            task_allowed_paths=None,
        )

    def _permission(self, role: str, command: str) -> str:
        from app.cli_runtime.agent_shell_hook import evaluate_hook_payload

        policy = self._policy(role)
        return evaluate_hook_payload(
            {"hook_event_name": "beforeShellExecution", "command": command},
            approved_wrappers=frozenset(policy.approved_wrappers),
            approved_command_prefixes=policy.approved_command_prefixes,
            allow_all_tools=policy.allow_all_tools,
        )["permission"]

    def test_implementation_roles_can_run_their_own_validation(self) -> None:
        for role in ("backend", "frontend", "integrations", "lead"):
            for command in (
                "npm ci",
                "npm test -- tests/x.test.ts",
                "npm run lint",
                "npx --no-install jest tests/x",
            ):
                with self.subTest(role=role, command=command):
                    self.assertEqual("allow", self._permission(role, command))

    def test_validation_roles_can_materialize_local_dependencies(self) -> None:
        from app.workspace_agents.execution_policy import role_execution_policy

        expected_dependency_roots = {
            "backend": "node_modules",
            "frontend": "node_modules",
            "integrations": "node_modules",
            "lead": "node_modules",
        }
        for role, root in expected_dependency_roots.items():
            with self.subTest(role=role):
                self.assertIn(root, role_execution_policy(role).write_paths)

    def test_full_access_allows_local_package_and_runtime_tools(self) -> None:
        for command in (
            "npm install lodash",
            "npx create-app",
            "npx jest tests/x",
            "node scripts/build.js",
            "python3 scripts/check.py",
            "curl https://example.invalid",
        ):
            with self.subTest(command=command):
                self.assertEqual("allow", self._permission("backend", command))

    def test_external_publication_commands_stay_gated(self) -> None:
        for command in (
            "npm run deploy",
            "npm publish",
            "vercel deploy --prod --yes",
            "eas submit --platform android",
            "supabase db push",
        ):
            with self.subTest(command=command):
                self.assertEqual("deny", self._permission("integrations", command))

    def test_ci_read_roles_can_probe_gh_but_not_mutate_it(self) -> None:
        for role in ("lead", "integrations"):
            with self.subTest(role=role):
                self.assertEqual("allow", self._permission(role, "gh auth status"))
                self.assertEqual("allow", self._permission(role, "gh run list"))
                self.assertEqual("deny", self._permission(role, "gh pr merge 12"))

    def test_every_role_can_reach_gh(self) -> None:
        self.assertEqual("allow", self._permission("backend", "gh auth status"))

    def test_watcher_has_the_same_tool_surface(self) -> None:
        self.assertEqual("allow", self._permission("watcher", "git status"))
        self.assertEqual("allow", self._permission("watcher", "npm test"))

    def test_privilege_and_destructive_git_guards_remain_separate(self) -> None:
        for command in ("sudo npm test", "git push origin main", "git reset --hard"):
            with self.subTest(command=command):
                self.assertEqual("deny", self._permission("backend", command))

    def test_document_roles_can_run_repo_python_scripts(self) -> None:
        for role in ("frontend", "lead", "backend"):
            with self.subTest(role=role):
                self.assertEqual(
                    "allow",
                    self._permission(role, "python3 scripts/fill-rfq26052-pdf.py"),
                )
                self.assertEqual("allow", self._permission(role, "pdftotext docs/rfq/form.pdf -"))


class LeadDispatchWrapperTests(unittest.TestCase):
    """A Lead without a dispatch wrapper can only write a handoff document."""

    def _permission(self, role: str, command: str) -> str:
        from app.cli_runtime.agent_shell_hook import evaluate_hook_payload
        from app.workspace_agents.execution_policy import resolve_effective_policy

        policy = resolve_effective_policy(
            role=role, workspace_allowed_paths=(".",), task_allowed_paths=None
        )
        return evaluate_hook_payload(
            {"hook_event_name": "beforeShellExecution", "command": command},
            approved_wrappers=frozenset(policy.approved_wrappers),
            approved_command_prefixes=policy.approved_command_prefixes,
            allow_all_tools=policy.allow_all_tools,
        )["permission"]

    def test_lead_can_fan_work_out_to_teammates(self) -> None:
        self.assertEqual(
            "allow",
            self._permission("lead", "axon-assign --workspace workspace_dashpro -- Fix red CI"),
        )

    def test_every_role_can_dispatch_when_the_task_needs_it(self) -> None:
        for role in ("backend", "frontend", "integrations", "watcher"):
            with self.subTest(role=role):
                self.assertEqual(
                    "allow",
                    self._permission(
                        role,
                        "axon-assign --workspace workspace_dashpro --role backend -- x",
                    ),
                )

    def test_watcher_can_look_up_run_evidence(self) -> None:
        self.assertEqual("allow", self._permission("watcher", "axon-runlog run_abc123"))

    def test_every_role_can_use_runlog(self) -> None:
        for role in ("lead", "backend", "frontend", "integrations"):
            with self.subTest(role=role):
                self.assertEqual("allow", self._permission(role, "axon-runlog run_abc123"))


if __name__ == "__main__":
    unittest.main()
