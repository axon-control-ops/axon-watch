from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from tests.support.bootstrap_signal_fixture import (
    BOOTSTRAP_WATCH_INBOX,
    CONSISTENCY_FIELDS,
    consistency_tuple,
)

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.inbox_projection import build_inbox_response, project_watch_inbox  # noqa: E402
from app.main import app  # noqa: E402


class ControlPlaneInboxProjectionTests(unittest.TestCase):
    def setUp(self) -> None:
        from app.persistence import run_store

        run_store.reset_store()
        self.client = TestClient(app)

    def test_project_watch_inbox_preserves_consistency_fields(self) -> None:
        projected = project_watch_inbox(BOOTSTRAP_WATCH_INBOX)
        source_item = BOOTSTRAP_WATCH_INBOX["items"][0]
        projected_item = projected["items"][0]

        for field in CONSISTENCY_FIELDS:
            self.assertEqual(source_item[field], projected_item[field])

    def test_inbox_endpoint_projects_watch_payload(self) -> None:
        with patch(
            "app.inbox_projection.fetch_watch_inbox",
            return_value=BOOTSTRAP_WATCH_INBOX,
        ):
            response = self.client.get("/api/inbox")

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual(1, payload["count"])
        projected_item = payload["items"][0]
        source_item = BOOTSTRAP_WATCH_INBOX["items"][0]
        self.assertEqual(consistency_tuple(source_item), consistency_tuple(projected_item))

    def test_build_inbox_response_returns_empty_snapshot_when_watch_unavailable(self) -> None:
        payload = build_inbox_response(inbox_fetcher=lambda: None)

        self.assertEqual([], payload["items"])
        self.assertEqual(0, payload["count"])


if __name__ == "__main__":
    unittest.main()
