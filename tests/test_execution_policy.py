from __future__ import annotations

import json
import sys
import tempfile
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path


CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.workspace_agents.config_loader import (  # noqa: E402
    WorkspaceAgentError,
    load_workspace_agent_configs,
)
from app.workspace_agents.execution_policy import (  # noqa: E402
    AgentExecutionPolicyOverride,
    resolve_effective_policy,
    role_execution_policy,
)


class RoleExecutionPolicyTests(unittest.TestCase):
    def test_role_defaults_are_immutable_and_conservative(self) -> None:
        lead = role_execution_policy("lead")
        watcher = role_execution_policy("watcher")
        frontend = role_execution_policy("frontend")
        backend = role_execution_policy("backend")
        integrations = role_execution_policy("integrations")

        self.assertEqual(("docs/planning", "docs/ops/agent-reports"), lead.write_paths)
        self.assertEqual((), watcher.write_paths)
        self.assertEqual("consultative", watcher.execution_access)
        self.assertEqual(("apps", "packages", "tests"), frontend.write_paths)
        self.assertEqual(("services", "packages", "tests"), backend.write_paths)
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

    def test_employee_override_can_only_reduce_authority(self) -> None:
        override = AgentExecutionPolicyOverride(
            approved_wrapper_names=("console-web.sh", "curl"),
            approved_command_prefixes=(
                ("npm", "run", "test", "--", "--run"),
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
            (("npm", "run", "test", "--", "--run"),),
            policy.approved_command_prefixes,
        )
        self.assertEqual(("test",), policy.audited_capabilities)
        self.assertEqual("none", policy.network_mode)
        self.assertEqual(1200, policy.timeout_seconds)
        self.assertEqual("worker", policy.trust_policy)
        self.assertEqual(("private/**", "**/.env"), policy.forbidden_path_globs)


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


if __name__ == "__main__":
    unittest.main()
