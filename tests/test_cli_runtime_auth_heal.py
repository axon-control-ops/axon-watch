"""CLI auth probe timeout heal / short-TTL cache behavior."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))


class CliRuntimeAuthHealTests(unittest.TestCase):
    def setUp(self) -> None:
        from app.cli_runtime import catalog_snapshot

        catalog_snapshot.invalidate_runtime_snapshot_cache()
        catalog_snapshot._LAST_HEAL_AT = 0.0

    def test_snapshot_detects_auth_probe_timeout(self) -> None:
        from app.cli_runtime.catalog_snapshot import snapshot_has_auth_probe_timeout

        self.assertTrue(
            snapshot_has_auth_probe_timeout(
                {
                    "local": [
                        {
                            "id": "cursor_local",
                            "auth": {
                                "logged_in": False,
                                "provider_label": "Timed out",
                                "message": "Cursor auth probe timed out. Run `cursor agent status` manually.",
                            },
                        }
                    ],
                    "cloud": [],
                }
            )
        )
        self.assertFalse(
            snapshot_has_auth_probe_timeout(
                {
                    "local": [
                        {
                            "id": "cursor_local",
                            "auth": {
                                "logged_in": True,
                                "provider_label": "Cursor",
                                "message": "Authenticated with Cursor subscription.",
                            },
                        }
                    ],
                    "cloud": [],
                }
            )
        )

    def test_cursor_auth_times_out_without_a_second_cli_process(self) -> None:
        import subprocess

        from app.cli_runtime.auth_probes import cursor_auth_status

        timed_out = subprocess.TimeoutExpired(cmd=["cursor", "agent", "status"], timeout=10)
        with patch(
            "app.cli_runtime.auth_probes._run_command",
            side_effect=timed_out,
        ) as run:
            result = cursor_auth_status(
                "/usr/bin/cursor",
                vault_posture={"unlocked": True, "posture": "ready", "runtime_keys": {}},
                env_keys={},
                probe_env={"NO_COLOR": "1"},
            )
        self.assertFalse(result["logged_in"])
        self.assertIn("timed out", result["message"].lower())
        self.assertEqual(1, run.call_count)

    def test_runtime_auth_gate_soft_opens_after_heal(self) -> None:
        from app.workspace_agents.scheduler_auto_start_gates import runtime_auth_blocks_auto_start

        with patch(
            "app.workspace_agents.scheduler_auto_start_gates.latest_role_run_outcome",
            return_value={
                "outcome": "failed",
                "detail": "Cursor auth probe timed out. Run `cursor agent status` manually.",
            },
        ), patch(
            "app.cli_runtime.catalog_snapshot.recover_cursor_auth_synchronously",
            return_value={
                "local": [
                    {
                        "id": "cursor_local",
                        "available": True,
                        "ready": True,
                        "auth": {
                            "logged_in": True,
                            "message": "Authenticated with Cursor subscription.",
                        },
                    }
                ],
                "cloud": [],
                "default_runtime": "cursor_local",
            },
        ):
            self.assertFalse(
                runtime_auth_blocks_auto_start("workspace_axon_watch", "backend")
            )


if __name__ == "__main__":
    unittest.main()
