from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(ROOT))

from app.local_notifications import notification_capability, notify_run_transition  # noqa: E402


class LocalNotificationTests(unittest.TestCase):
    @patch("app.local_notifications.shutil.which", return_value="/usr/bin/notify-send")
    def test_capability_requires_desktop_bus(self, _which) -> None:
        self.assertFalse(notification_capability({"PATH": "/usr/bin"})["enabled"])
        self.assertTrue(
            notification_capability(
                {"PATH": "/usr/bin", "DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/user/1/bus"}
            )["enabled"]
        )

    @patch("app.local_notifications.notification_capability", return_value={"enabled": True})
    @patch("app.local_notifications.shutil.which", return_value="/usr/bin/notify-send")
    @patch("app.local_notifications.subprocess.run")
    def test_review_ready_notification_includes_sound_hint(self, run, _which, _capability) -> None:
        run.return_value.returncode = 0
        self.assertTrue(notify_run_transition({"phase": "review_ready", "summary": "Ready"}))
        self.assertIn("--hint=string:sound-name:message-new-instant", run.call_args.args[0])

    @patch("app.local_notifications.notification_capability", return_value={"enabled": True})
    @patch("app.local_notifications.shutil.which", return_value="/usr/bin/notify-send")
    @patch("app.local_notifications.subprocess.run")
    def test_notification_cleans_prompt_headings_and_names_role(self, run, _which, _capability) -> None:
        run.return_value.returncode = 0
        notify_run_transition({
            "phase": "failed", "role": "frontend",
            "summary": "# Instructions\n## Objective\nFix the dashboard layout",
        })
        self.assertEqual("Frontend: Fix the dashboard layout", run.call_args.args[0][-1])

    @patch("app.local_notifications.subprocess.run")
    def test_executing_phase_does_not_notify(self, run) -> None:
        self.assertFalse(notify_run_transition({"phase": "executing"}))
        run.assert_not_called()
