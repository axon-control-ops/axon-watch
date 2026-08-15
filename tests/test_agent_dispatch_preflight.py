from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.cli_runtime.agent_dispatch_preflight import validate_agent_dispatch_preflight  # noqa: E402
from app.cli_runtime.agent_sandbox import AgentSandboxPolicy, SandboxConfigurationError  # noqa: E402
from app.workspace_agents.execution_policy import role_execution_policy  # noqa: E402


class AgentDispatchPreflightTests(unittest.TestCase):
    def test_missing_bwrap_fails_before_dispatch(self) -> None:
        policy = role_execution_policy("lead")
        with patch("app.cli_runtime.agent_dispatch_preflight.shutil.which", return_value=None):
            with self.assertRaisesRegex(SandboxConfigurationError, "Bubblewrap"):
                validate_agent_dispatch_preflight(
                    family="cursor",
                    runtime_binary="/usr/bin/true",
                    sandbox_policy=policy,
                )

    def test_missing_ripgrep_fails_with_actionable_message(self) -> None:
        policy = role_execution_policy("integrations")

        def _which(name: str) -> str | None:
            if name == "bwrap":
                return "/usr/bin/bwrap"
            return None

        with patch("app.cli_runtime.agent_dispatch_preflight.shutil.which", side_effect=_which):
            with self.assertRaisesRegex(SandboxConfigurationError, "ripgrep"):
                validate_agent_dispatch_preflight(
                    family="cursor",
                    runtime_binary="/usr/bin/true",
                    sandbox_policy=policy,
                )

    def test_no_policy_skips_sandbox_checks(self) -> None:
        validate_agent_dispatch_preflight(
            family="cursor",
            runtime_binary="/usr/bin/true",
            sandbox_policy=None,
        )


if __name__ == "__main__":
    unittest.main()
