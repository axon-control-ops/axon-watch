from __future__ import annotations

import json
import sys
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from tests.support.control_plane_app_loader import prepare_control_plane_imports
from tests.support.control_plane_db import isolate_control_plane_db

from scripts.verify.common import load_config  # noqa: E402

_CANONICAL_TOP_LEVEL_KEYS = {
    "generated_at",
    "control_plane",
    "watch",
    "runtime_identity",
    "active_runs",
    "approvals",
    "signals",
    "connectors",
    "cli_runtime",
    "capabilities",
    "degraded",
}


class ControlPlaneRuntimeSummaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self._saved_modules = prepare_control_plane_imports()
        self.addCleanup(self._restore_control_plane_modules)

        from app.main import app
        from app.persistence import run_store

        isolate_control_plane_db(self, run_store)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def _restore_control_plane_modules(self) -> None:
        for name in list(sys.modules):
            if name == "app" or name.startswith("app."):
                del sys.modules[name]
        sys.modules.update(self._saved_modules)

    def test_runtime_summary_endpoint_returns_assembled_canonical_shape(self) -> None:
        with patch(
            "app.runtime_summary_assembler.default_watch_probe",
            return_value=(True, "ok", None, "2026-07-03T15:00:00Z"),
        ):
            response = self.client.get("/api/runtime/summary")

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual(_CANONICAL_TOP_LEVEL_KEYS, set(payload))
        self.assertTrue(payload["control_plane"]["ready"])
        self.assertIn("provider_name", payload["runtime_identity"])
        self.assertEqual([], payload["active_runs"])

    def test_runtime_summary_endpoint_marks_degraded_when_watch_unavailable(self) -> None:
        with patch(
            "app.runtime_summary_assembler.default_watch_probe",
            return_value=(False, "unavailable", "watch probe failed", "2026-07-03T15:00:00Z"),
        ):
            response = self.client.get("/api/runtime/summary")

        payload = response.json()
        self.assertFalse(payload["watch"]["connected"])
        self.assertTrue(payload["degraded"]["active"])

    def test_runtime_summary_endpoint_counts_pending_approvals(self) -> None:
        self.client.post(
            "/api/runs",
            json={
                "workspace_id": "workspace_alpha",
                "mode": "agent",
                "summary": "Approval summary run",
                "requires_approval": True,
            },
        )

        with patch(
            "app.runtime_summary_assembler.default_watch_probe",
            return_value=(True, "ok", None, "2026-07-03T15:00:00Z"),
        ):
            response = self.client.get("/api/runtime/summary")

        payload = response.json()
        self.assertEqual(1, payload["approvals"]["pending_count"])
        self.assertIsNotNone(payload["approvals"]["latest_approval_at"])

    def test_runtime_summary_endpoint_payload_fits_size_budget(self) -> None:
        with patch(
            "app.runtime_summary_assembler.default_watch_probe",
            return_value=(True, "ok", None, "2026-07-03T15:00:00Z"),
        ):
            response = self.client.get("/api/runtime/summary")

        encoded = json.dumps(response.json(), separators=(",", ":"), ensure_ascii=False).encode(
            "utf-8"
        )
        threshold = int(load_config()["dto_sizes"]["runtime_summary"]["threshold_bytes"])
        self.assertLessEqual(len(encoded), threshold)


if __name__ == "__main__":
    unittest.main()
