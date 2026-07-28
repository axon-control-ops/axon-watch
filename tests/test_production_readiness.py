from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.production_readiness import build_production_readiness  # noqa: E402


class ProductionReadinessTests(unittest.TestCase):
    def test_ready_when_core_surfaces_healthy(self) -> None:
        payload = build_production_readiness(
            watch_connected=True,
            control_plane_ready=True,
            degraded_active=False,
            cli_runtime={
                "dispatch_ready": True,
                "default_ready": True,
                "blockers": [],
            },
            critical_signal_count=0,
            pending_approvals=0,
            autonomy_mode="semi",
        )
        self.assertEqual(100, payload["score"])
        self.assertEqual("ready", payload["grade"])
        self.assertEqual([], payload["blockers"])
        self.assertIn("Production is 100%", payload["summary"])

    def test_cli_auth_timeout_blocks_ready_grade(self) -> None:
        payload = build_production_readiness(
            watch_connected=True,
            control_plane_ready=True,
            degraded_active=False,
            cli_runtime={
                "dispatch_ready": False,
                "default_ready": False,
                "blockers": ["Cursor auth probe timed out"],
            },
            critical_signal_count=0,
            pending_approvals=0,
            autonomy_mode="manual",
        )
        self.assertLess(payload["score"], 80)
        self.assertEqual("partial", payload["grade"])
        self.assertTrue(
            any("Cursor auth" in item for item in payload["blockers"]),
        )

    def test_full_mode_requires_effective_scheduler(self) -> None:
        payload = build_production_readiness(
            watch_connected=True,
            control_plane_ready=True,
            degraded_active=False,
            cli_runtime={
                "dispatch_ready": True,
                "default_ready": True,
                "blockers": [],
            },
            autonomy_mode="full",
            scheduler_effective=False,
        )
        self.assertIn(
            "continuous workers are not effective",
            " ".join(payload["blockers"]).lower(),
        )


if __name__ == "__main__":
    unittest.main()
