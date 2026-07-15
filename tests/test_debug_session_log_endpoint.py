from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.main import app  # noqa: E402


class DebugSessionLogEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def test_debug_ingest_is_hidden_by_default(self) -> None:
        with patch.dict(os.environ, {"AXON_DEBUG_SESSION_LOG": ""}, clear=False):
            response = self.client.post(
                "/api/dev/debug-session-log",
                json={
                    "hypothesisId": "H1",
                    "location": "test",
                    "message": "disabled",
                },
            )

        self.assertEqual(404, response.status_code)

    def test_debug_ingest_appends_only_when_explicitly_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir, patch.dict(
            os.environ,
            {"AXON_DEBUG_SESSION_LOG": "1"},
            clear=False,
        ), patch(
            "app.terminal.workspace_roots.resolve_workspace_root",
            return_value=Path(temp_dir),
        ):
            response = self.client.post(
                "/api/dev/debug-session-log",
                json={
                    "hypothesisId": "H2",
                    "location": "runtime",
                    "message": "enabled",
                    "data": {"count": 1},
                    "workspace_id": "workspace_alpha",
                },
            )

            self.assertEqual(200, response.status_code)
            log_path = Path(temp_dir) / ".axon" / "debug-session.ndjson"
            payload = json.loads(log_path.read_text(encoding="utf-8").strip())

        self.assertEqual("H2", payload["hypothesisId"])
        self.assertEqual({"count": 1}, payload["data"])


if __name__ == "__main__":
    unittest.main()
