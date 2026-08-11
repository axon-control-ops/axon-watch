from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.cli_runtime.sandbox_policy_adapter import (  # noqa: E402
    adapt_execution_policy,
    prepare_execution_sandbox,
)
from app.workspace_agents.execution_policy import role_execution_policy  # noqa: E402


class SandboxPolicyAdapterTests(unittest.TestCase):
    def test_cursor_mounts_only_exact_runtime_and_auth_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "home"
            binary = home / ".local/share/cursor-agent/version/cursor-agent"
            binary.parent.mkdir(parents=True)
            binary.write_text("#!/bin/sh\n", encoding="utf-8")
            for relative in (
                ".cursor/cli-config.json",
                ".cursor/agent-cli-state.json",
                ".config/cursor/auth.json",
            ):
                path = home / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("{}", encoding="utf-8")
            with patch(
                "app.cli_runtime.sandbox_policy_adapter.Path.home",
                return_value=home,
            ):
                sandbox = adapt_execution_policy(
                    role_execution_policy("watcher"),
                    runtime_binary=str(binary),
                    family="cursor",
                )

        mounted = set(sandbox.cursor_readonly_paths)
        self.assertIn(str(binary.parent), mounted)
        self.assertIn(str(home / ".config/cursor/auth.json"), mounted)
        self.assertNotIn(str(home / ".config"), mounted)
        self.assertNotIn(str(home / ".cursor"), mounted)

    def test_claude_and_codex_mount_their_own_subscription_credentials(self) -> None:
        """Regression: sandboxed claude/codex dispatch always reported "not
        logged in" because only the cursor family's auth files were ever
        bind-mounted into the sandbox's rewritten HOME — the CLI was fully
        authenticated on the host but the sandbox exposed no credentials.
        """
        for family, relative in (
            ("claude", ".claude/.credentials.json"),
            ("codex", ".codex/auth.json"),
        ):
            with self.subTest(family=family):
                with tempfile.TemporaryDirectory() as directory:
                    home = Path(directory) / "home"
                    binary = home / ".local/bin" / family
                    binary.parent.mkdir(parents=True)
                    binary.write_text("#!/bin/sh\n", encoding="utf-8")
                    creds = home / relative
                    creds.parent.mkdir(parents=True, exist_ok=True)
                    creds.write_text("{}", encoding="utf-8")
                    with patch(
                        "app.cli_runtime.sandbox_policy_adapter.Path.home",
                        return_value=home,
                    ):
                        sandbox = adapt_execution_policy(
                            role_execution_policy("lead"),
                            runtime_binary=str(binary),
                            family=family,
                        )
                mounted = set(sandbox.cursor_readonly_paths)
                self.assertIn(str(creds), mounted)

    def test_missing_credentials_file_is_not_mounted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "home"
            binary = home / ".local/bin/claude"
            binary.parent.mkdir(parents=True)
            binary.write_text("#!/bin/sh\n", encoding="utf-8")
            with patch(
                "app.cli_runtime.sandbox_policy_adapter.Path.home",
                return_value=home,
            ):
                sandbox = adapt_execution_policy(
                    role_execution_policy("lead"),
                    runtime_binary=str(binary),
                    family="claude",
                )
        mounted = set(sandbox.cursor_readonly_paths)
        self.assertFalse(any(".credentials.json" in path for path in mounted))

    def test_npm_style_bin_layout_also_mounts_package_root(self) -> None:
        """codex/claude resolve sibling optional/native deps via node_modules
        walk-up from their own package root, not just their bin/ directory —
        exposing bin/ alone left codex's own module resolution finding
        nothing inside the sandbox (regression: reported as "Missing optional
        dependency @openai/codex-linux-x64" even on a real, working install).
        """
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "home"
            package_root = home / ".nvm/versions/node/v20/lib/node_modules/@openai/codex"
            bin_dir = package_root / "bin"
            bin_dir.mkdir(parents=True)
            binary = bin_dir / "codex.js"
            binary.write_text("#!/usr/bin/env node\n", encoding="utf-8")
            with patch(
                "app.cli_runtime.sandbox_policy_adapter.Path.home",
                return_value=home,
            ):
                sandbox = adapt_execution_policy(
                    role_execution_policy("watcher"),
                    runtime_binary=str(binary),
                    family="codex",
                )

        mounted = set(sandbox.cursor_readonly_paths)
        self.assertIn(str(bin_dir), mounted)
        self.assertIn(str(package_root), mounted, "package root must be exposed alongside bin/")

    def test_prepare_adds_identity_env_only_when_policy_exists(self) -> None:
        env = {"SAFE": "1"}
        unchanged, sandbox = prepare_execution_sandbox(
            None,
            family="cursor",
            runtime_binary="/missing",
            env=env,
            workspace_id="workspace_demo",
            run_id="run_demo",
        )
        self.assertIs(env, unchanged)
        self.assertIsNone(sandbox)

    def test_codex_uses_a_private_sandbox_home_not_a_hidden_host_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / "codex"
            binary.write_text("#!/bin/sh\n", encoding="utf-8")
            env, sandbox = prepare_execution_sandbox(
                role_execution_policy("lead"),
                family="codex",
                runtime_binary=str(binary),
                env={"CODEX_HOME": str(Path(directory) / "missing-profile")},
                workspace_id="workspace_demo",
                run_id="run_demo",
            )

        self.assertEqual("/run/axon-agent-home/.codex", env["CODEX_HOME"])
        self.assertIsNotNone(sandbox)
        self.assertEqual("", sandbox.codex_auth_path)  # type: ignore[union-attr]


if __name__ == "__main__":
    unittest.main()
