"""HTTP tests for durable plan routes."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.main import app  # noqa: E402
from app.persistence import run_store  # noqa: E402
from app.plans.service import capture_plan_from_reply  # noqa: E402

COMPLETE_PLAN = """# View Plan slice

## Goal
Persist durable plans and open them from chat.

## Steps
1. Capture complete Plan-mode replies only
2. Render the amber View Plan card in transcript
3. Open markdown preview from the plan artifact API

## Verification
- GET /api/plans returns the new plan id
- View Plan opens read-only preview content
"""


class ControlPlanePlansTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)
        self.workspace_tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.workspace_tempdir.cleanup)
        self.root = Path(self.workspace_tempdir.name)
        self.root_patch = patch(
            "app.plans.file_store.resolve_workspace_root",
            return_value=self.root,
        )
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)
        self.env_patch = patch.dict(
            os.environ,
            {"AXON_WATCH_WORKSPACE_ROOT": self.workspace_tempdir.name},
            clear=False,
        )
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def test_list_and_get_plan(self) -> None:
        record, _ = capture_plan_from_reply(
            workspace_id="workspace_alpha",
            thread_id="thread_plan",
            source_message_id="message_agent_plan",
            content=COMPLETE_PLAN,
        )
        listed = self.client.get("/api/plans?workspace_id=workspace_alpha")
        self.assertEqual(200, listed.status_code)
        payload = listed.json()
        self.assertGreaterEqual(payload["count"], 1)
        ids = {item["plan_id"] for item in payload["items"]}
        self.assertIn(record.plan_id, ids)
        self.assertNotIn("content", payload["items"][0])

        got = self.client.get(
            f"/api/plans/{record.plan_id}?workspace_id=workspace_alpha"
        )
        self.assertEqual(200, got.status_code)
        body = got.json()
        self.assertEqual(record.plan_id, body["plan_id"])
        self.assertEqual("View Plan slice", body["title"])
        self.assertIn("Capture", body["content"])

    def test_get_missing_plan_returns_404(self) -> None:
        response = self.client.get(
            "/api/plans/plan_deadbeefdead?workspace_id=workspace_alpha"
        )
        self.assertEqual(404, response.status_code)

    def test_workspace_isolation(self) -> None:
        record, _ = capture_plan_from_reply(
            workspace_id="workspace_alpha",
            thread_id="thread_plan",
            source_message_id="message_agent_plan",
            content=COMPLETE_PLAN.replace("View Plan slice", "Isolated"),
        )
        with tempfile.TemporaryDirectory() as other_dir:
            with patch(
                "app.plans.file_store.resolve_workspace_root",
                return_value=Path(other_dir),
            ):
                response = self.client.get(
                    f"/api/plans/{record.plan_id}?workspace_id=workspace_dashpro"
                )
                self.assertEqual(404, response.status_code)


if __name__ == "__main__":
    unittest.main()
