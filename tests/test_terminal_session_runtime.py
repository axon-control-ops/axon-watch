"""Terminal profile titles select the requested PTY shell."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.terminal.session_registry import TerminalSessionRecord  # noqa: E402
from app.terminal.session_runtime import ensure_runtime, reset_runtimes  # noqa: E402


class TerminalSessionRuntimeTests(unittest.TestCase):
    def tearDown(self) -> None:
        reset_runtimes()

    @patch("app.terminal.session_runtime.PtyProcess")
    def test_operator_bash_profile_stays_bash(self, pty_process) -> None:
        session = TerminalSessionRecord(
            session_id="terminal-bash-test",
            workspace_id="workspace_test",
            role="operator",
            title="bash",
            run_id=None,
            created_at="2026-07-30T00:00:00Z",
        )

        ensure_runtime(
            workspace_id=session.workspace_id,
            workspace_root="/tmp",
            session=session,
        )

        self.assertEqual("bash", pty_process.call_args.kwargs["preferred_shell"])

    @patch("app.terminal.session_runtime.PtyProcess")
    def test_blank_operator_profile_defaults_to_zsh(self, pty_process) -> None:
        session = TerminalSessionRecord(
            session_id="terminal-default-test",
            workspace_id="workspace_test",
            role="operator",
            title="",
            run_id=None,
            created_at="2026-07-30T00:00:00Z",
        )

        ensure_runtime(
            workspace_id=session.workspace_id,
            workspace_root="/tmp",
            session=session,
        )

        self.assertEqual("zsh", pty_process.call_args.kwargs["preferred_shell"])


if __name__ == "__main__":
    unittest.main()
