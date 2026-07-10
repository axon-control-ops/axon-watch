"""Tests for watch + control-plane Sentry resolve wiring."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

WATCH_SERVICE_ROOT = Path(__file__).resolve().parents[1] / "services" / "axon-watch"
CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"


def _reset_app_modules() -> None:
    for module_name in list(sys.modules):
        if module_name == "app" or module_name.startswith("app."):
            sys.modules.pop(module_name, None)


def _prefer_path(root: Path) -> None:
    root_s = str(root)
    while root_s in sys.path:
        sys.path.remove(root_s)
    sibling = str(WATCH_SERVICE_ROOT if root == CONTROL_PLANE_ROOT else CONTROL_PLANE_ROOT)
    while sibling in sys.path:
        sys.path.remove(sibling)
    sys.path.insert(0, root_s)


class WatchSentryResolveRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        _reset_app_modules()
        _prefer_path(WATCH_SERVICE_ROOT)
        from app.main import app as watch_app  # noqa: E402

        self.client = TestClient(watch_app)

    def tearDown(self) -> None:
        _reset_app_modules()

    def test_resolve_route_returns_ok_payload(self) -> None:
        with patch(
            "app.main.resolve_watch_sentry_issue",
            return_value={"ok": True, "issue_id": "42", "status": "resolved", "requested_by": "operator"},
        ):
            response = self.client.post("/internal/watch/sentry/issues/42/resolve", json={})
        self.assertEqual(200, response.status_code)
        self.assertTrue(response.json()["ok"])

    def test_resolve_route_maps_failure_to_400(self) -> None:
        with patch(
            "app.main.resolve_watch_sentry_issue",
            return_value={"ok": False, "reason": "missing_write_scope", "issue_id": "42"},
        ):
            response = self.client.post("/internal/watch/sentry/issues/42/resolve", json={})
        self.assertEqual(400, response.status_code)
        self.assertEqual("missing_write_scope", response.json()["detail"]["reason"])

    def test_probe_write_route(self) -> None:
        with patch(
            "app.main.probe_watch_sentry_write_scope",
            return_value={"ok": True, "write_scope": True},
        ):
            response = self.client.post("/internal/watch/sentry/probe-write")
        self.assertEqual(200, response.status_code)
        self.assertTrue(response.json()["write_scope"])


class ControlPlaneSentryResolveRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        _reset_app_modules()
        _prefer_path(CONTROL_PLANE_ROOT)
        from app.routes.inbox_watch import router  # noqa: E402

        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)

    def tearDown(self) -> None:
        _reset_app_modules()

    def test_api_resolve_proxies_ok(self) -> None:
        with patch(
            "app.routes.inbox_watch.post_watch_sentry_issue_resolve",
            return_value={"ok": True, "issue_id": "7", "status": "resolved"},
        ):
            response = self.client.post("/api/sentry/issues/7/resolve", json={"requested_by": "operator"})
        self.assertEqual(200, response.status_code)
        self.assertEqual("7", response.json()["issue_id"])

    def test_api_resolve_maps_failure(self) -> None:
        with patch(
            "app.routes.inbox_watch.post_watch_sentry_issue_resolve",
            return_value={"ok": False, "reason": "missing_config"},
        ):
            response = self.client.post("/api/sentry/issues/7/resolve", json={})
        self.assertEqual(400, response.status_code)

    def test_api_probe_write(self) -> None:
        with patch(
            "app.routes.inbox_watch.post_watch_sentry_probe_write",
            return_value={"ok": False, "write_scope": False, "reason": "missing_write_scope"},
        ):
            response = self.client.post("/api/sentry/probe-write")
        self.assertEqual(200, response.status_code)
        self.assertFalse(response.json()["write_scope"])


if __name__ == "__main__":
    unittest.main()
