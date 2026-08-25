"""Focused contracts for platform process and doctor reporting."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))


class ProcessInventoryTests(unittest.TestCase):
    def test_listener_without_resolved_pid_is_not_reported_as_stopped(self) -> None:
        from app.platform_recovery.process_inventory import inspect_processes

        with (
            patch("app.platform_recovery.process_inventory._port_pid", return_value=None),
            patch("app.platform_recovery.process_inventory._port_listening", return_value=True),
            patch("app.platform_recovery.process_inventory._scan_test_processes", return_value=[]),
        ):
            rows = inspect_processes()

        self.assertTrue(rows)
        self.assertTrue(all(row["state"] == "listening" for row in rows))
        self.assertTrue(all(row["owner"] == "listener pid unavailable" for row in rows))


class PlatformDoctorTests(unittest.TestCase):
    def test_listening_services_pass_without_false_start_instructions(self) -> None:
        from app.platform_recovery.doctor import run_doctor

        processes = [
            {"port": port, "state": "listening", "process": name}
            for port, name in ((4173, "console-web"), (8787, "control-plane"), (8788, "axon-watch"))
        ]
        with (
            patch("app.platform_recovery.doctor.inspect_processes", return_value=processes),
            patch(
                "app.platform_recovery.doctor.build_recovery_center",
                return_value={"attention_count": 0, "counts": {}},
            ),
            patch("app.platform_recovery.doctor.list_circuits", return_value=[]),
        ):
            result = run_doctor()

        checks = {item["name"]: item for item in result["checks"]}
        for name in ("control_plane", "watch", "frontend"):
            self.assertEqual("PASS", checks[name]["status"])
            self.assertIn("listening", checks[name]["next_action"].lower())
            self.assertNotIn("start", checks[name]["next_action"].lower())


if __name__ == "__main__":
    unittest.main()
