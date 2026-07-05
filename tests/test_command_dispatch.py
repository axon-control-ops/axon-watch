"""Tests for operator command dispatch naming."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.chat.command_intent import command_display_name  # noqa: E402
from app.chat.dispatch import summarize_command_for_run  # noqa: E402


class CommandDispatchNamingTests(unittest.TestCase):
    def test_command_display_name_maps_supported_commands(self) -> None:
        self.assertEqual("Health check", command_display_name("health"))
        self.assertEqual("Git status", command_display_name("git status"))
        self.assertEqual("Read README.md", command_display_name("read README.md"))
        self.assertEqual("List workspace files", command_display_name("ls"))

    def test_summarize_command_for_run_uses_display_name(self) -> None:
        self.assertEqual("Health check", summarize_command_for_run("health"))
        self.assertEqual("Read notes.txt", summarize_command_for_run("cat notes.txt"))


if __name__ == "__main__":
    unittest.main()
