from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.chat.command_executor import CommandExecutionResult  # noqa: E402
from app.main import app  # noqa: E402
from app.persistence import chat_store, run_store  # noqa: E402


class ControlPlaneChatHealthTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)
        chat_store.reset_store()
        self.addCleanup(chat_store.reset_store)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def test_health_probe_completes_run_and_records_receipt(self) -> None:
        with patch(
            "app.chat.command_executor.execute_health_probe",
            return_value=CommandExecutionResult(
                intent="health_probe",
                success=True,
                output='{"status": "ok"}',
                receipt_summary="Health probe succeeded",
            ),
        ):
            response = self.client.post(
                "/api/chat/messages",
                json={
                    "workspace_id": "workspace_alpha",
                    "content": "curl -s http://127.0.0.1:8787/api/health",
                },
            )

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertTrue(payload["dispatched"])
        self.assertEqual("completed", payload["run"]["phase"])
        self.assertIn("health_probe", payload["messages"][2]["content"])
        self.assertIn("```", payload["messages"][2]["content"])

        history = self.client.get(f"/api/runs/{payload['run_id']}/history").json()
        receipt_types = [item["receipt"]["type"] for item in history["items"]]
        self.assertIn("command_execution", receipt_types)
        self.assertIn("operator_complete", receipt_types)


if __name__ == "__main__":
    unittest.main()
