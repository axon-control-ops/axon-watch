from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from tests.support.bootstrap_signal_fixture import (
    BOOTSTRAP_WATCH_INBOX,
    CONSISTENCY_FIELDS,
    consistency_tuple,
)
from tests.support.control_plane_app_loader import prepare_control_plane_imports
from tests.support.control_plane_db import isolate_control_plane_db


class ControlPlaneInboxProjectionTests(unittest.TestCase):
    def setUp(self) -> None:
        prepare_control_plane_imports()
        from app.inbox_projection import (  # noqa: WPS433
            WatchInboxUnavailableError,
            build_inbox_response,
            project_inbox_item,
            project_watch_inbox,
        )
        from app.main import app  # noqa: WPS433
        from app.persistence import run_store  # noqa: WPS433

        self.WatchInboxUnavailableError = WatchInboxUnavailableError
        self.build_inbox_response = build_inbox_response
        self.project_inbox_item = project_inbox_item
        self.project_watch_inbox = project_watch_inbox
        isolate_control_plane_db(self, run_store)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def test_project_watch_inbox_preserves_consistency_fields(self) -> None:
        projected = self.project_watch_inbox(BOOTSTRAP_WATCH_INBOX)
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

    def test_project_inbox_item_feeds_known_pattern_into_meta_override(self) -> None:
        projected = self.project_inbox_item(
            {
                "signal_id": "signal_x",
                "severity": "critical",
                "title": "DashPro Sentry critical",
                "summary": "Sentry API rejected the auth token",
            }
        )
        self.assertIn("operator_what", projected["meta"])
        self.assertIn("operator_you_do", projected["meta"])
        self.assertIn("Vault", projected["meta"]["operator_you_do"])

    def test_project_inbox_item_does_not_overwrite_existing_meta_override(self) -> None:
        projected = self.project_inbox_item(
            {
                "signal_id": "signal_x",
                "severity": "critical",
                "title": "DashPro Sentry critical",
                "summary": "Sentry API rejected the auth token",
                "meta": {"operator_what": "a more specific upstream explanation"},
            }
        )
        self.assertEqual("a more specific upstream explanation", projected["meta"]["operator_what"])

    def test_build_inbox_response_fails_closed_when_watch_unavailable(self) -> None:
        with self.assertRaises(self.WatchInboxUnavailableError):
            self.build_inbox_response(inbox_fetcher=lambda: None)

    def test_inbox_endpoint_returns_503_when_watch_unavailable(self) -> None:
        with patch(
            "app.inbox_projection.fetch_watch_inbox",
            return_value=None,
        ):
            response = self.client.get("/api/inbox")
        self.assertEqual(503, response.status_code)


if __name__ == "__main__":
    unittest.main()
