from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.chat.command_executor import classify_command, execute_command  # noqa: E402
from app.chat.shell_command import (  # noqa: E402
    extract_shell_command_line,
    validate_shell_command_line,
)


class ShellCommandTests(unittest.TestCase):
    def test_extract_run_prefix(self) -> None:
        self.assertEqual(extract_shell_command_line("run npm test"), "npm test")
        self.assertIsNone(extract_shell_command_line("npm test"))

    def test_validate_blocks_shell_metacharacters(self) -> None:
        blocked = validate_shell_command_line("npm test && rm -rf /")
        self.assertFalse(blocked.ok)

    def test_classify_run_prefix(self) -> None:
        self.assertEqual(classify_command("run npm test"), "shell_command")

    def test_execute_run_command_in_workspace_root(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir) / "workspace_alpha"
            root.mkdir()
            (root / "marker.txt").write_text("ok\n", encoding="utf-8")

            with patch.dict("os.environ", {"AXON_WATCH_WORKSPACE_ROOT": tempdir}, clear=False):
                result = execute_command(
                    workspace_id="workspace_alpha",
                    content="run ls marker.txt",
                )

            self.assertTrue(result.success)
            self.assertEqual("shell_command", result.intent)
            self.assertIn("marker.txt", result.output)


if __name__ == "__main__":
    unittest.main()
