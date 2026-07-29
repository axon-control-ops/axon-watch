from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.terminal.shell_invocation import (  # noqa: E402
    build_shell_command,
    build_shell_env,
    bundled_bash_rc_path,
    resolve_terminal_shell,
    zdotdir_path,
)


class ShellInvocationTests(unittest.TestCase):
    def test_resolve_terminal_shell_prefers_session_title(self) -> None:
        self.assertTrue(resolve_terminal_shell("zsh").endswith("zsh"))
        self.assertTrue(resolve_terminal_shell("bash").endswith("bash"))

    def test_build_shell_command_uses_zdotdir_for_zsh_not_rcfile(self) -> None:
        self.assertEqual(build_shell_command("/bin/zsh"), ["/bin/zsh", "-i"])
        self.assertFalse(any("--rcfile" in part for part in build_shell_command("/bin/zsh")))

    def test_build_shell_command_uses_interactive_rc_for_bash(self) -> None:
        self.assertEqual(
            build_shell_command("/bin/bash"),
            ["/bin/bash", "--rcfile", str(bundled_bash_rc_path()), "-i"],
        )

    def test_build_shell_env_sets_workspace_history_and_zdotdir_for_zsh(self) -> None:
        env = build_shell_env({}, workspace_root="/tmp/workspace_smoke", shell="/bin/zsh")

        self.assertEqual(env["PWD"], "/tmp/workspace_smoke")
        self.assertEqual(env["STARSHIP_DISABLED"], "1")
        self.assertEqual(env["HISTFILE"], "/tmp/workspace_smoke/.axon_terminal_history")
        self.assertEqual(env["ZDOTDIR"], str(zdotdir_path()))
        self.assertEqual(env["SAVEHIST"], "5000")
        self.assertTrue((zdotdir_path() / ".zshrc").is_file())

    def test_bundled_zshrc_prefers_host_oh_my_zsh_when_present(self) -> None:
        text = (zdotdir_path() / ".zshrc").read_text(encoding="utf-8")
        self.assertIn("oh-my-zsh.sh", text)
        self.assertIn("AXON_WATCH_DISABLE_OMZ", text)
        self.assertIn("robbyrussell", text)


if __name__ == "__main__":
    unittest.main()
