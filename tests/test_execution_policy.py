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

    def test_role_defaults_are_immutable_and_conservative(self) -> None:
        lead = role_execution_policy("lead")
        watcher = role_execution_policy("watcher")
        frontend = role_execution_policy("frontend")
        backend = role_execution_policy("backend")
        integrations = role_execution_policy("integrations")

        self.assertIn("docs/ops", lead.write_paths)
        self.assertEqual((), watcher.write_paths)
        self.assertEqual("consultative", watcher.execution_access)
        self.assertIn("components", frontend.write_paths)
        self.assertIn("hooks", frontend.write_paths)
        self.assertIn("services", backend.write_paths)
        self.assertNotIn("apps", integrations.write_paths)
        self.assertTrue(
            all(policy.trust_policy == "worker" for policy in (
                lead,
                watcher,
                frontend,
                backend,
                integrations,
            ))
        )
        with self.assertRaises(FrozenInstanceError):
            backend.timeout_seconds = 1  # type: ignore[misc]

    def test_unknown_role_falls_back_to_read_only(self) -> None:
        policy = role_execution_policy("custom")
        self.assertEqual((), policy.write_paths)
        self.assertEqual("consultative", policy.execution_access)
        self.assertEqual("none", policy.network_mode)


class EffectiveExecutionPolicyTests(unittest.TestCase):
    def test_scope_is_narrowest_prefix_across_every_authority(self) -> None:
        override = AgentExecutionPolicyOverride(
            read_paths=("services/control-plane", "tests"),
            write_paths=("services/control-plane", "tests"),
        )
        policy = resolve_effective_policy(
            role="backend",
            employee_override=override,
            workspace_allowed_paths=("services", "tests", "config"),
            workspace_forbidden_path_globs=("**/.env",),
            task_allowed_paths=("services/control-plane/app/workspace_agents",),
        )

        self.assertEqual(("services/control-plane", "tests"), policy.read_paths)
        self.assertEqual(
            ("services/control-plane/app/workspace_agents",),
            policy.write_paths,
        )
        self.assertEqual(("**/.env",), policy.forbidden_path_globs)
        self.assertEqual("full", policy.execution_access)

    def test_empty_task_scope_means_no_writes(self) -> None:
        policy = resolve_effective_policy(
            role="backend",
            workspace_allowed_paths=("services", "tests"),
            task_allowed_paths=[],
        )

        self.assertEqual((), policy.write_paths)
        self.assertEqual("consultative", policy.execution_access)

    def test_missing_task_scope_uses_the_role_ceiling(self) -> None:
        policy = resolve_effective_policy(
            role="backend",
            workspace_allowed_paths=("services", "tests"),
            task_allowed_paths=None,
        )

        self.assertEqual(("services", "tests"), policy.write_paths)
        self.assertEqual("full", policy.execution_access)

    def test_frontend_ui_task_scope_restores_safe_hooks_root(self) -> None:
        policy = resolve_effective_policy(
            role="frontend",
            workspace_allowed_paths=("app", "components", "hooks", "tests"),
            task_allowed_paths=("app", "components", "tests"),
        )

        self.assertIn("hooks", policy.write_paths)
        self.assertEqual("full", policy.execution_access)

    def test_safe_scope_expansion_stays_role_and_contract_bounded(self) -> None:
        backend = resolve_effective_policy(
            role="backend",
            workspace_allowed_paths=("services", "hooks", "tests"),
            task_allowed_paths=("services",),
        )
        missing_contract = resolve_effective_policy(
            role="frontend",
            workspace_allowed_paths=("app", "components", "tests"),
            task_allowed_paths=("app", "components", "tests"),
        )

        self.assertNotIn("hooks", backend.write_paths)
        self.assertNotIn("hooks", missing_contract.write_paths)

    def test_missing_or_disjoint_scope_fails_closed(self) -> None:
        missing_contract = resolve_effective_policy(
            role="frontend",
            workspace_allowed_paths=None,
            task_allowed_paths=("apps",),
        )
        disjoint_task = resolve_effective_policy(
            role="frontend",
            workspace_allowed_paths=("apps",),
            task_allowed_paths=("services",),
        )

        self.assertEqual((), missing_contract.read_paths)
        self.assertEqual((), missing_contract.write_paths)
        self.assertEqual((), disjoint_task.write_paths)

    def test_ops_dashboard_contract_grants_frontend_command_centre_writes(self) -> None:
        allowed = (
            "package.json",
            "scripts/",
            "server/",
            "command-centre/",
            "data/live/",
            "data/exports/",
            "docs/ops/",
            "output/homework/",
            "output/poems/",
        )
        policy = resolve_effective_policy(
            role="frontend",
            workspace_allowed_paths=allowed,
            task_allowed_paths=None,
        )

        self.assertIn("command-centre", policy.write_paths)
        self.assertTrue(any(path.startswith("output/") for path in policy.write_paths))
        self.assertEqual("full", policy.execution_access)

    def test_employee_override_can_only_reduce_authority(self) -> None:
        override = AgentExecutionPolicyOverride(
            approved_wrapper_names=("console-web.sh", "curl"),
            approved_command_prefixes=(
                ("git", "status", "--short"),
                ("curl",),
            ),
            audited_capabilities=("test", "secrets_write"),
            network_mode="unrestricted",
            timeout_seconds=2400,
            trust_policy="operator",
            execution_access="full",
            forbidden_path_globs=("private/**",),
        )
        policy = resolve_effective_policy(
            role="frontend",
            employee_override=override,
            workspace_allowed_paths=("apps", "tests"),
            workspace_forbidden_path_globs=("**/.env",),
            task_allowed_paths=("apps/console-web",),
        )

        self.assertEqual(("console-web.sh",), policy.approved_wrapper_names)
        self.assertEqual(
            (("git", "status", "--short"),),
            policy.approved_command_prefixes,
        )
        self.assertEqual(("test",), policy.audited_capabilities)
        self.assertEqual("none", policy.network_mode)
        self.assertEqual(1200, policy.timeout_seconds)
        self.assertEqual("worker", policy.trust_policy)
        self.assertEqual(("private/**", "**/.env"), policy.forbidden_path_globs)

    def test_legacy_empty_task_scope_is_recovered_at_the_worker_boundary(self) -> None:
        # Pre-default task rows persisted an omitted allowed_paths as [], which
        # would otherwise make every queued specialist task consultative.
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
            workspace_allowed_paths=(),
            task_allowed_paths=None,
        )

    def _permission(self, role: str, command: str) -> str:
        from app.cli_runtime.agent_shell_hook import evaluate_hook_payload

        policy = self._policy(role)
        return evaluate_hook_payload(
            {"hook_event_name": "beforeShellExecution", "command": command},
            approved_wrappers=frozenset(policy.approved_wrappers),
            approved_command_prefixes=policy.approved_command_prefixes,
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

        for role in ("backend", "frontend", "integrations", "lead"):
            with self.subTest(role=role):
                self.assertIn("node_modules", role_execution_policy(role).write_paths)

    def test_mutating_package_commands_stay_gated(self) -> None:
        for command in (
            "npm install lodash",
            "npm run deploy",
            "npm publish",
            "npx create-app",
            "npx jest tests/x",
        ):
            with self.subTest(command=command):
                self.assertEqual("deny", self._permission("backend", command))

    def test_ci_read_roles_can_probe_gh_but_not_mutate_it(self) -> None:
        for role in ("lead", "integrations"):
            with self.subTest(role=role):
                self.assertEqual("allow", self._permission(role, "gh auth status"))
                self.assertEqual("allow", self._permission(role, "gh run list"))
                self.assertEqual("deny", self._permission(role, "gh pr merge 12"))

    def test_roles_without_ci_read_still_cannot_reach_gh(self) -> None:
        self.assertEqual("deny", self._permission("backend", "gh auth status"))

    def test_consultative_watcher_stays_read_only(self) -> None:
        self.assertEqual("allow", self._permission("watcher", "git status"))
        self.assertEqual("deny", self._permission("watcher", "npm test"))

    def test_interpreter_and_privilege_escapes_remain_absolute(self) -> None:
        for command in ('node -e "1"', "bash -c ls", "sudo npm test", "curl https://x.invalid"):
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
            role=role, workspace_allowed_paths=(), task_allowed_paths=None
        )
        return evaluate_hook_payload(
            {"hook_event_name": "beforeShellExecution", "command": command},
            approved_wrappers=frozenset(policy.approved_wrappers),
            approved_command_prefixes=policy.approved_command_prefixes,
        )["permission"]

    def test_lead_can_fan_work_out_to_teammates(self) -> None:
        self.assertEqual(
            "allow",
            self._permission("lead", "axon-assign --workspace workspace_dashpro -- Fix red CI"),
        )

    def test_specialists_cannot_dispatch_each_other(self) -> None:
        for role in ("backend", "frontend", "integrations", "watcher"):
            with self.subTest(role=role):
                self.assertEqual(
                    "deny",
                    self._permission(role, "axon-assign --workspace workspace_dashpro -- x"),
                )

    def test_watcher_can_look_up_run_evidence(self) -> None:
        self.assertEqual("allow", self._permission("watcher", "axon-runlog run_abc123"))

    def test_only_watcher_can_use_runlog(self) -> None:
        for role in ("lead", "backend", "frontend", "integrations"):
            with self.subTest(role=role):
                self.assertEqual("deny", self._permission(role, "axon-runlog run_abc123"))


if __name__ == "__main__":
    unittest.main()
