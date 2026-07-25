from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.routes import register_routes  # noqa: E402
from app.safe_improvement import session as sandbox_session  # noqa: E402


class SafeImprovementGateTests(unittest.TestCase):
    def setUp(self) -> None:
        sandbox_session.reset_session_for_tests()

    def tearDown(self) -> None:
        sandbox_session.reset_session_for_tests()

    def test_proposal_routes_are_absent_by_default(self) -> None:
        with patch.dict(os.environ, {"AXON_SAFE_IMPROVEMENT_ENABLED": ""}, clear=False):
            app = FastAPI()
            register_routes(app)

        with TestClient(app) as client:
            response = client.get("/api/safe-improvement/proposals")
        self.assertEqual(404, response.status_code)

    def test_session_status_is_always_available(self) -> None:
        with patch.dict(os.environ, {"AXON_SAFE_IMPROVEMENT_ENABLED": ""}, clear=False):
            app = FastAPI()
            register_routes(app)
            with TestClient(app) as client:
                response = client.get("/api/safe-improvement/session")

        self.assertEqual(200, response.status_code)
        body = response.json()
        self.assertFalse(body["enabled"])
        self.assertEqual("off", body["source"])

    def test_button_can_enable_sandbox_session(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(
                os.environ,
                {
                    "AXON_SAFE_IMPROVEMENT_ENABLED": "",
                    "AXON_WATCH_CONTROL_PLANE_DB": str(Path(temp_dir) / "gate.sqlite3"),
                },
                clear=False,
            ):
                app = FastAPI()
                register_routes(app)
                with TestClient(app) as client:
                    enable = client.post("/api/safe-improvement/session/enable")
                    self.assertEqual(200, enable.status_code)
                    self.assertTrue(enable.json()["enabled"])
                    self.assertEqual("session", enable.json()["source"])

                    proposals = client.get("/api/safe-improvement/proposals")
                    self.assertEqual(200, proposals.status_code)

                    disable = client.post("/api/safe-improvement/session/disable")
                    self.assertEqual(200, disable.status_code)
                    self.assertFalse(disable.json()["enabled"])

                    blocked = client.get("/api/safe-improvement/proposals")
                    self.assertEqual(404, blocked.status_code)

    def test_operator_can_explicitly_enable_routes_via_env(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(
                os.environ,
                {
                    "AXON_SAFE_IMPROVEMENT_ENABLED": "1",
                    "AXON_WATCH_CONTROL_PLANE_DB": str(Path(temp_dir) / "gate.sqlite3"),
                },
                clear=False,
            ):
                app = FastAPI()
                register_routes(app)
                with TestClient(app) as client:
                    response = client.get("/api/safe-improvement/proposals")
                    status = client.get("/api/safe-improvement/session")

        self.assertEqual(200, response.status_code)
        self.assertEqual(200, status.status_code)
        self.assertTrue(status.json()["enabled"])
        self.assertEqual("env", status.json()["source"])


if __name__ == "__main__":
    unittest.main()
