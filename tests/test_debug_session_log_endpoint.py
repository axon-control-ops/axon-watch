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

    def test_debug_log_read_returns_recent_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir, patch(
            "app.terminal.workspace_roots.resolve_workspace_root",
            return_value=Path(temp_dir),
        ):
            axon_dir = Path(temp_dir) / ".axon"
            axon_dir.mkdir(parents=True, exist_ok=True)
            log_path = axon_dir / "debug-session.ndjson"
            log_path.write_text(
                json.dumps(
                    {
                        "hypothesisId": "H3",
                        "location": "thread",
                        "message": "visible in panel",
                        "data": {},
                        "timestamp": 1,
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            response = self.client.get(
                "/api/dev/debug-session-log",
                params={"workspace_id": "workspace_alpha", "limit": 10},
            )

        self.assertEqual(200, response.status_code)
        body = response.json()
        self.assertTrue(body["ok"])
        self.assertEqual(1, body["count"])
        self.assertEqual("H3", body["entries"][0]["hypothesisId"])
        self.assertEqual("visible in panel", body["entries"][0]["message"])


if __name__ == "__main__":
    unittest.main()
