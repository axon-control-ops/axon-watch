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
from app.persistence import run_store  # noqa: E402


class ControlPlaneOperatorPresenceTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def test_briefing_operator_presence_marks_spoken_alert_for_approval(self) -> None:
        self.client.post(
            "/api/runs",
            json={
                "workspace_id": "workspace_alpha",
                "mode": "agent",
                "summary": "Approval-bound run",
                "detail": "Awaiting explicit approval",
                "requires_approval": True,
            },
        )

        response = self.client.get("/api/briefing")
        self.assertEqual(200, response.status_code)
        presence = response.json()["operator_presence"]
        self.assertEqual("alerting", presence["presence_state"])
        self.assertTrue(presence["spoken_alert"]["eligible"])
        self.assertEqual("operator_approval_required", presence["spoken_alert"]["reason"])

    def test_briefing_viewport_compact_sets_mobile_layout(self) -> None:
        response = self.client.get("/api/briefing?viewport_compact=true")
        self.assertEqual(200, response.status_code)
        self.assertTrue(response.json()["operator_presence"]["mobile"]["compact_layout"])


if __name__ == "__main__":
    unittest.main()
