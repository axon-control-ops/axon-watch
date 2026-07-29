"""Phase 4 E2E: control-plane skeleton APIs assemble runtime truth from live endpoints."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from tests.support.control_plane_db import isolate_control_plane_db
from tests.support.ephemeral_uvicorn import EphemeralUvicorn
from tests.support.watch_app_loader import load_watch_app, restore_app_modules

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"


class ControlPlaneSkeletonE2ETests(unittest.TestCase):
    def setUp(self) -> None:
        # Load watch first in isolation, then restore and import control-plane so
        # ``app.vault.watch_adapter`` resolves to the CP package (not axon-watch).
        watch_app, self._pre_watch_modules = load_watch_app()
        self._watch_server = EphemeralUvicorn(watch_app)
        self._watch_server.start("/internal/watch/health")
        restore_app_modules(self._pre_watch_modules)

        sys.path.insert(0, str(CONTROL_PLANE_ROOT))
        from app.main import app  # noqa: WPS433
        from app.persistence import run_store  # noqa: WPS433

        isolate_control_plane_db(self, run_store)
        self._env_patch = patch.dict(
            os.environ,
            {"AXON_WATCH_WATCH_SERVICE_BASE_URL": self._watch_server.base_url},
            clear=False,
        )
        self._env_patch.start()
        self.addCleanup(self._env_patch.stop)

        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def tearDown(self) -> None:
        self._watch_server.stop()
        restore_app_modules(self._pre_watch_modules)

    def test_runtime_summary_and_workspaces_render_from_live_apis(self) -> None:
        workspaces = self.client.get("/api/workspaces").json()
        summary = self.client.get("/api/runtime/summary").json()

        self.assertGreaterEqual(len(workspaces["items"]), 1)
        self.assertTrue(summary["control_plane"]["ready"])
        self.assertTrue(summary["watch"]["connected"])
        self.assertIn("runtime_identity", summary)
        self.assertIn("active_runs", summary)

    def test_create_run_appears_in_run_list_and_runtime_summary(self) -> None:
        create_response = self.client.post(
            "/api/runs",
            json={
                "workspace_id": "workspace_smoke",
                "mode": "agent",
                "summary": "Phase 4 E2E run",
                "detail": "Skeleton verification run",
            },
        )
        self.assertEqual(200, create_response.status_code)
        created = create_response.json()

        list_response = self.client.get("/api/runs")
        self.assertEqual(200, list_response.status_code)
        listed_ids = {row["run_id"] for row in list_response.json()["items"]}
        self.assertIn(created["run_id"], listed_ids)

        summary = self.client.get("/api/runtime/summary").json()
        active_ids = {row["run_id"] for row in summary["active_runs"]}
        self.assertIn(created["run_id"], active_ids)
        self.assertEqual("executing", created["phase"])
