"""G4.4 voice cockpit slice tests."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


class VoiceCockpitSliceTests(unittest.TestCase):
    def test_voice_cockpit_config_present(self) -> None:
        path = REPO_ROOT / "config" / "voice-cockpit-slice.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertTrue(payload.get("enabled"))
        self.assertIn("live_events_presence_refresh", payload["event_sources"])

    def test_live_events_emits_presence_refresh(self) -> None:
        live_events = (REPO_ROOT / "services/control-plane/app/live_events.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("presence_refresh", live_events)

    def test_voice_cockpit_modules_wired_in_app(self) -> None:
        app_vue = (REPO_ROOT / "apps/console-web/src/App.vue").read_text(encoding="utf-8")
        self.assertIn("useVoiceCockpitPresence", app_vue)
        self.assertIn("MobileVoiceCockpitStrip", app_vue)
        self.assertIn("onPresenceRefresh", app_vue)


class AgentDockParitySliceTests(unittest.TestCase):
    def test_dock_contract_checker_passes(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/verify/check_dock_behavior_contract.py"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, msg=result.stderr or result.stdout)

    def test_agent_dock_thread_meta_and_collapsible_thread_seam(self) -> None:
        agent_dock = (
            REPO_ROOT / "apps/console-web/src/components/ide/AgentDock.vue"
        ).read_text(encoding="utf-8")
        right_dock = (
            REPO_ROOT / "apps/console-web/src/components/shell/RightDock.vue"
        ).read_text(encoding="utf-8")
        self.assertIn("agent-dock__section-meta", agent_dock)
        self.assertIn("toggleDockSeam('thread')", right_dock)


if __name__ == "__main__":
    unittest.main()
