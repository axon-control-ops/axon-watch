from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.cli_runtime.agent_dispatch_preflight import (  # noqa: E402
    validate_agent_dispatch_preflight,
    validate_sandbox_workspace_toolchain,
)
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

    def test_toolchain_preflight_skips_without_isolation_sidecar(self) -> None:
        with patch(
            "app.cli_runtime.sandbox_preview.ensure_isolation_checkout_runnable"
        ) as ensure:
            validate_sandbox_workspace_toolchain(Path("/tmp/no-sidecar-checkout"))
            ensure.assert_not_called()

    def test_toolchain_preflight_raises_when_borrow_is_not_runnable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            checkout = Path(tmp)
            sidecar_dir = checkout / ".axon-si"
            sidecar_dir.mkdir()
            (sidecar_dir / "baseline.json").write_text("{}", encoding="utf-8")
            with patch(
                "app.cli_runtime.sandbox_preview.ensure_isolation_checkout_runnable",
                return_value={"ok": False, "errors": ["jest: not found in node_modules/.bin"]},
            ):
                with self.assertRaisesRegex(
                    SandboxConfigurationError, "Sandbox checkout toolchain is not runnable"
                ):
                    validate_sandbox_workspace_toolchain(checkout)


if __name__ == "__main__":
    unittest.main()
