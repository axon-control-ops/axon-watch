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


class SafeImprovementGateTests(unittest.TestCase):
    def test_routes_are_absent_by_default(self) -> None:
        with patch.dict(os.environ, {"AXON_SAFE_IMPROVEMENT_ENABLED": ""}, clear=False):
            app = FastAPI()
            register_routes(app)

        with TestClient(app) as client:
            response = client.get("/api/safe-improvement/proposals")
        self.assertEqual(404, response.status_code)

    def test_operator_can_explicitly_enable_routes(self) -> None:
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

        self.assertEqual(200, response.status_code)


if __name__ == "__main__":
    unittest.main()
