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

    def test_pressure_marks_fat_tsserver_auto_killable(self) -> None:
        from app.host_context import machine_pulse as mp

        self.assertTrue(
            mp._is_auto_killable(
                name="tsserver[5.9.2]",
                cmdline="tsserver[5.9.2]: semantic",
                rss=250.0,
                protected=False,
                junk=False,
                mem_pct=85.0,
            )
        )
        self.assertFalse(
            mp._is_auto_killable(
                name="tsserver[5.9.2]",
                cmdline="tsserver[5.9.2]: semantic",
                rss=1573.0,
                protected=False,
                junk=False,
                mem_pct=70.0,
            )
        )

    def test_orphan_si_worker_not_ide_protected(self) -> None:
        from app.host_context import machine_pulse as mp

        self.assertFalse(
            mp._is_protected(
                "MainThread",
                "/home/edp/.local/bin/cursor-agent ... /tmp/axon-si-run_abc/checkout ...",
                pid=424242,
            )
        )

    def test_ci_runner_worker_is_reclaimable_under_pressure(self) -> None:
        from app.host_context import machine_pulse as mp

        cmdline = (
            "/srv/axon-server/actions-runner-dashpro/_work/_tool/node/20/bin/node "
            ".../jest-worker/build/workers/processChild.js"
        )
        self.assertFalse(mp._is_protected("node", cmdline, pid=424243))
        self.assertTrue(
            mp._is_auto_killable(
                name="node",
                cmdline=cmdline,
                rss=90.0,
                protected=False,
                junk=False,
                mem_pct=85.0,
                swap_pct=80.0,
            )
        )


if __name__ == "__main__":
    unittest.main()
