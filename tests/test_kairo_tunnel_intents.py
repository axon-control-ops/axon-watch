"""VAXON early intent: repair / restart the public tunnel."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.kairo_tunnel_intents import (  # noqa: E402
    detect_public_tunnel_repair_intent,
    maybe_handle_public_tunnel_repair_intent,
)


class PublicTunnelRepairIntentTests(unittest.TestCase):
    def test_detects_operator_fix_phrases(self) -> None:
        self.assertTrue(detect_public_tunnel_repair_intent("FIX THE PUBLIC TUNNEL"))
        self.assertTrue(detect_public_tunnel_repair_intent("please restart the remote ingress"))
        self.assertTrue(detect_public_tunnel_repair_intent("public tunnel is down"))
        self.assertFalse(detect_public_tunnel_repair_intent("fix the GitHub API warning"))
        self.assertFalse(detect_public_tunnel_repair_intent("what is the tunnel status?"))

    def test_starts_tunnel_via_watch_and_returns_action(self) -> None:
        with patch(
            "app.adapters.watch_client.fetch_watch_tunnel",
            side_effect=[
                {"running": False, "status": "stopped", "url": "https://axon.edudashpro.org.za"},
                {
                    "running": True,
                    "status": "ok",
                    "url": "https://axon.edudashpro.org.za",
                    "detail": "active",
                },
            ],
        ), patch(
            "app.adapters.watch_client.post_watch_tunnel_action",
            return_value={
                "running": True,
                "status": "ok",
                "url": "https://axon.edudashpro.org.za",
                "detail": "active",
            },
        ) as start:
            payload = maybe_handle_public_tunnel_repair_intent(
                content="FIX THE PUBLIC TUNNEL",
                session_id="test-session",
                guest_name=None,
            )
        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual("action", payload["turn_kind"])
        self.assertEqual("start_tunnel", payload["action"]["type"])
        self.assertEqual("started", payload["action"]["outcome"])
        self.assertIn("Restarted the public tunnel", payload["reply"])
        start.assert_called_once_with("start", timeout_seconds=90.0)

    def test_specialty_handoff_skips_tunnel_repair(self) -> None:
        from app.kairo.teammate_handoff import build_specialty_task_action

        self.assertIsNone(
            build_specialty_task_action(
                "FIX THE PUBLIC TUNNEL",
                workspace_id="workspace_axon_watch",
            )
        )


if __name__ == "__main__":
    unittest.main()
