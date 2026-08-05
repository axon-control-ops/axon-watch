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
                    include_cursor_auth=True,
                )

        mounted = set(sandbox.cursor_readonly_paths)
        self.assertIn(str(binary.parent), mounted)
        self.assertIn(str(home / ".config/cursor/auth.json"), mounted)
        self.assertNotIn(str(home / ".config"), mounted)
        self.assertNotIn(str(home / ".cursor"), mounted)

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
                    include_cursor_auth=False,
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


if __name__ == "__main__":
    unittest.main()
