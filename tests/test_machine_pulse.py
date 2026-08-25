"""Machine CEO host pulse + safe kill policy."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_ROOT))

from app.host_context.machine_ceo import kill_process, run_machine_ceo_tick  # noqa: E402
from app.host_context.machine_pulse import build_machine_pulse  # noqa: E402


class MachinePulseTests(unittest.TestCase):
    def test_pulse_reads_linux_proc(self) -> None:
        pulse = build_machine_pulse(process_limit=8)
        self.assertTrue(pulse["ok"])
        self.assertIn("health", pulse)
        self.assertIn("memory_percent", pulse["health"])
        self.assertIsInstance(pulse["processes"], list)
        self.assertTrue(pulse["spoken"])
        # Self should be protected if listed.
        self_rows = [row for row in pulse["processes"] if row["pid"] == os.getpid()]
        if self_rows:
            self.assertTrue(self_rows[0]["protected"])

    def test_refuses_to_kill_self(self) -> None:
        result = kill_process(os.getpid(), require_auto_eligible=False)
        self.assertFalse(result["ok"])
        self.assertIn(result.get("reason"), {"protected", "not_in_pulse_snapshot"})

    def test_ceo_tick_skips_kills_when_not_full(self) -> None:
        with patch(
            "app.host_context.machine_ceo._autonomy_full",
            return_value=False,
        ):
            tick = run_machine_ceo_tick(auto_kill=True)
        self.assertTrue(tick["ok"])
        self.assertFalse(tick["autonomy_full"])
        self.assertEqual(tick["kills"], [])


if __name__ == "__main__":
    unittest.main()
