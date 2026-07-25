from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.main import app  # noqa: E402


class ControlPlaneKairoRuleTests(unittest.TestCase):
    def setUp(self) -> None:
        from app.persistence import run_store

        isolate_control_plane_db(self, run_store)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def test_inbox_projection_preserves_watch_rule(self) -> None:
        watch_inbox = {
            "items": [
                {
                    "signal_id": "signal_runtime_summary_degraded",
                    "workspace_id": "workspace_alpha",
                    "title": "Watch summary degraded",
                    "summary": "Watch summary is degraded.",
                    "severity": "high",
                    "status": "open",
                    "source": "watch",
                    "created_at": "2026-07-03T15:01:00Z",
                    "updated_at": "2026-07-03T15:02:00Z",
                    "action_type": "open_dashboard",
                    "delivery_state": "delivered",
                    "watch_rule": {
                        "mode": "observe",
                        "reason": "bootstrap_summary_stale",
                        "interrupts": False,
                    },
                }
            ],
            "count": 1,
            "updated_at": "2026-07-03T15:02:00Z",
        }
        with patch(
            "app.inbox_projection.fetch_watch_inbox",
            return_value=watch_inbox,
        ):
            response = self.client.get("/api/inbox")

        rule = response.json()["items"][0]["watch_rule"]
        self.assertEqual("observe", rule["mode"])
        self.assertEqual("bootstrap_summary_stale", rule["reason"])


if __name__ == "__main__":
    unittest.main()
