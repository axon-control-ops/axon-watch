from __future__ import annotations

import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.devices import store as device_store  # noqa: E402
from app.main import app  # noqa: E402
from app.persistence import run_store  # noqa: E402


class DeviceEnrollmentApiTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)
        device_store.reset_store()
        self.addCleanup(device_store.reset_store)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def test_enroll_list_and_revoke(self) -> None:
        enrolled = self.client.post(
            "/api/devices/enroll",
            json={
                "label": "pixel-lab",
                "platform": "android",
                "capabilities": ["wake.local", "converse"],
            },
        )
        self.assertEqual(200, enrolled.status_code, enrolled.text)
        body = enrolled.json()
        self.assertEqual("active", body["status"])
        self.assertTrue(body["device_id"].startswith("dev_"))
        self.assertEqual(["wake.local", "converse"], body["capabilities"])
        device_id = body["device_id"]

        listed = self.client.get("/api/devices")
        self.assertEqual(200, listed.status_code)
        self.assertEqual(1, listed.json()["count"])
        self.assertEqual(device_id, listed.json()["items"][0]["device_id"])

        got = self.client.get(f"/api/devices/{device_id}")
        self.assertEqual(200, got.status_code)
        self.assertEqual("pixel-lab", got.json()["label"])

        revoked = self.client.post(f"/api/devices/{device_id}/revoke")
        self.assertEqual(200, revoked.status_code)
        self.assertEqual("revoked", revoked.json()["status"])
        self.assertIsNotNone(revoked.json()["revoked_at"])

        active_only = self.client.get("/api/devices", params={"status": "active"})
        self.assertEqual(0, active_only.json()["count"])
        revoked_only = self.client.get("/api/devices", params={"status": "revoked"})
        self.assertEqual(1, revoked_only.json()["count"])

    def test_revoke_unknown_device_is_404(self) -> None:
        response = self.client.post("/api/devices/missing/revoke")
        self.assertEqual(404, response.status_code)

    def test_enroll_requires_label(self) -> None:
        response = self.client.post("/api/devices/enroll", json={"label": "  "})
        self.assertIn(response.status_code, {400, 422})

    def test_idempotent_reenroll_same_device_id(self) -> None:
        first = self.client.post(
            "/api/devices/enroll",
            json={"label": "one", "platform": "android", "device_id": "dev_fixed_1"},
        )
        self.assertEqual(200, first.status_code)
        second = self.client.post(
            "/api/devices/enroll",
            json={
                "label": "two",
                "platform": "android",
                "device_id": "dev_fixed_1",
                "capabilities": ["tts"],
            },
        )
        self.assertEqual(200, second.status_code)
        self.assertEqual("dev_fixed_1", second.json()["device_id"])
        self.assertEqual("two", second.json()["label"])
        self.assertEqual(["tts"], second.json()["capabilities"])
        self.assertEqual(1, self.client.get("/api/devices").json()["count"])


if __name__ == "__main__":
    unittest.main()
