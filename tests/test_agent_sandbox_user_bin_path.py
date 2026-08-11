from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from app.cli_runtime.agent_sandbox import (
    AgentSandboxPolicy,
    build_bwrap_command,
    materialize_cursor_hook_policy,
)


class AgentSandboxUserBinPathTests(unittest.TestCase):
    def test_bwrap_exposes_user_local_bin_for_authenticated_cli_tools(self) -> None:
        temp_root = Path(tempfile.mkdtemp(prefix="axon-agent-sandbox-bin-test-"))
        try:
            workspace = temp_root / "workspace"
            home = temp_root / "home"
            local_bin = home / ".local" / "bin"
            workspace.mkdir()
            local_bin.mkdir(parents=True)
            (local_bin / "gh").write_text("#!/bin/sh\necho gh\n", encoding="utf-8")
            policy = AgentSandboxPolicy()
            material = materialize_cursor_hook_policy(
                policy=policy,
                run_id="run-user-bin",
                workspace_root=workspace,
                policy_root=temp_root / "policies",
            )

            command = build_bwrap_command(
                ["/bin/true"],
                policy=policy,
                workspace_root=workspace,
                hook_material=material,
                bwrap_path="/usr/bin/bwrap",
                user_home=home,
            )

            self.assertIn(str(local_bin), command)
            self.assertIn(str(local_bin), command[command.index("PATH") + 1].split(":"))
        finally:
            shutil.rmtree(temp_root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
