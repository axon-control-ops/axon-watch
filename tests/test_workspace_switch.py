from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.chat.workspace_switch import (  # noqa: E402
    build_workspace_switch_reply,
    resolve_workspace_switch_intent,
    workspace_switch_ui_action,
)


class WorkspaceSwitchIntentTests(unittest.TestCase):
    def test_resolves_dashpro_workspace_prompt(self) -> None:
        intent = resolve_workspace_switch_intent("Open and switch to the Dashpro workspace")
        self.assertIsNotNone(intent)
        assert intent is not None
        self.assertEqual("workspace_dashpro", intent.target_workspace_id)
        self.assertEqual("DashPro", intent.display_name)

    def test_ignores_unrelated_prompts(self) -> None:
        self.assertIsNone(resolve_workspace_switch_intent("explain README.md"))
        self.assertIsNone(resolve_workspace_switch_intent("git status"))

    def test_builds_reply_and_ui_action(self) -> None:
        intent = resolve_workspace_switch_intent("switch to dashpro workspace")
        self.assertIsNotNone(intent)
        assert intent is not None
        reply = build_workspace_switch_reply(intent)
        self.assertIn("workspace_dashpro", reply)
        action = workspace_switch_ui_action(intent)
        self.assertEqual("switch_workspace", action["type"])
        self.assertEqual("workspace_dashpro", action["workspace_id"])


if __name__ == "__main__":
    unittest.main()
