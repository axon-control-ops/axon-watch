from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.cli_runtime.agent_process_scope import (  # noqa: E402
    agent_scope_enabled,
    agent_scope_memory_high,
    agent_scope_unit_from_wrapped_command,
    stop_agent_scope,
    wrap_command_in_agent_scope,
)


class AgentProcessScopeTests(unittest.TestCase):
    def test_wrap_command_passthrough_when_scope_disabled(self) -> None:
        command = ["cursor-agent", "--print", "hello"]
        with patch.dict(os.environ, {"AXON_WATCH_AGENT_SYSTEMD_SCOPE": "0"}, clear=False):
            self.assertFalse(agent_scope_enabled())
            self.assertEqual(command, wrap_command_in_agent_scope(command))

    def test_memory_high_defaults_below_2g_max(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual("1536M", agent_scope_memory_high())

    def test_wrap_command_passthrough_when_systemd_unavailable(self) -> None:
        command = ["cursor-agent", "--print", "hello"]
        with patch.dict(os.environ, {"AXON_WATCH_AGENT_SYSTEMD_SCOPE": "1"}, clear=False), patch(
            "app.cli_runtime.agent_process_scope._systemd_user_available",
            return_value=False,
        ):
            self.assertEqual(command, wrap_command_in_agent_scope(command))

    def test_wrap_command_prefixes_systemd_run_when_available(self) -> None:
        command = ["cursor-agent", "--print", "hello"]
        with patch.dict(
            os.environ,
            {
                "AXON_WATCH_AGENT_SYSTEMD_SCOPE": "1",
                "AXON_WATCH_AGENT_MEMORY_MAX": "2G",
                "AXON_WATCH_AGENT_MEMORY_HIGH": "1536M",
            },
            clear=False,
        ), patch(
            "app.cli_runtime.agent_process_scope._systemd_user_available",
            return_value=True,
        ):
            wrapped = wrap_command_in_agent_scope(command)
        self.assertEqual("systemd-run", wrapped[0])
        self.assertIn("--user", wrapped)
        self.assertIn("--scope", wrapped)
        self.assertIn("--property=MemoryMax=2G", wrapped)
        self.assertIn("--property=MemoryHigh=1536M", wrapped)
        separator = wrapped.index("--")
        self.assertEqual(command, wrapped[separator + 1 :])

    def test_wrap_command_suppresses_systemd_run_banner(self) -> None:
        """Regression: without --quiet, systemd-run's own "Running scope as
        unit: ...; invocation ID: ..." banner lands on stderr and — when the
        wrapped CLI fails without emitting its own parseable error — gets
        surfaced to the operator as if it were the failure reason, masking
        whatever actually went wrong (e.g. a real Cursor/Codex/Claude error).
        """
        with patch.dict(
            os.environ,
            {"AXON_WATCH_AGENT_SYSTEMD_SCOPE": "1"},
            clear=False,
        ), patch(
            "app.cli_runtime.agent_process_scope._systemd_user_available",
            return_value=True,
        ):
            wrapped = wrap_command_in_agent_scope(["cursor-agent", "--print", "hello"])
        self.assertIn("--quiet", wrapped)

    def test_unit_name_extracted_from_wrapped_command(self) -> None:
        wrapped = wrap_command_in_agent_scope(["cursor-agent", "--print", "hello"])
        unit = agent_scope_unit_from_wrapped_command(wrapped)
        if wrapped[0] == "systemd-run":
            self.assertIsNotNone(unit)
            self.assertTrue(str(unit).startswith("axon-agent-"))
        else:
            self.assertIsNone(unit)

    def test_stop_agent_scope_invokes_systemctl(self) -> None:
        with patch(
            "app.cli_runtime.agent_process_scope._systemd_user_available",
            return_value=True,
        ), patch(
            "app.cli_runtime.agent_process_scope.shutil.which",
            return_value="/usr/bin/systemctl",
        ), patch(
            "app.cli_runtime.agent_process_scope.subprocess.run",
            return_value=MagicMock(returncode=0),
        ) as run_mock:
            self.assertTrue(stop_agent_scope("axon-agent-deadbeef"))
        run_mock.assert_called_once()
        self.assertEqual(
            ["/usr/bin/systemctl", "--user", "stop", "axon-agent-deadbeef.scope"],
            run_mock.call_args.args[0],
        )


if __name__ == "__main__":
    unittest.main()
