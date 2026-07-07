from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.main import app  # noqa: E402
from app.persistence import run_store  # noqa: E402

_RUNTIME_SUMMARY = {
    "generated_at": "2026-07-07T21:00:00Z",
    "watch": {"connected": True},
    "degraded": {"active": False, "reasons": []},
}

_INBOX = {
    "items": [
        {
            "signal_id": "signal_sentry_spike",
            "workspace_id": "workspace_dashpro",
            "title": "Sentry error spike",
            "summary": "Errors up 40%",
            "severity": "high",
            "status": "open",
            "source": "watch",
            "updated_at": "2026-07-07T21:00:00Z",
            "action_type": "open_dashboard",
        }
    ],
    "count": 1,
    "updated_at": "2026-07-07T21:00:00Z",
}

_CONNECTORS = {
    "items": [
        {
            "connector_id": "control_plane",
            "display_name": "Control plane",
            "required": True,
            "workspace_id": "workspace_axon_watch",
            "status": "ok",
            "detail": "ok",
        },
        {
            "connector_id": "axon_local",
            "display_name": "axon-local (legacy)",
            "required": False,
            "workspace_id": "workspace_axon_local",
            "status": "unavailable",
            "detail": "connection refused",
        },
    ],
    "count": 2,
}


class OperatorBrainGraphTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def _get_graph(self) -> dict[str, object]:
        with patch(
            "app.operator_brain_graph.assemble_runtime_summary",
            return_value=_RUNTIME_SUMMARY,
        ), patch(
            "app.operator_brain_graph.build_inbox_response",
            return_value=_INBOX,
        ), patch(
            "app.operator_brain_graph.fetch_watch_connectors",
            return_value=_CONNECTORS,
        ):
            response = self.client.get("/api/operator/brain-graph")
        self.assertEqual(200, response.status_code)
        return response.json()

    def test_graph_contains_core_signal_and_connector_nodes(self) -> None:
        payload = self._get_graph()

        node_ids = {node["node_id"] for node in payload["nodes"]}
        self.assertIn("core_kairo", node_ids)
        self.assertIn("sig_signal_sentry_spike", node_ids)
        self.assertIn("conn_control_plane", node_ids)
        self.assertIn("conn_axon_local", node_ids)
        self.assertEqual(payload["node_count"], len(payload["nodes"]))
        self.assertEqual(payload["edge_count"], len(payload["edges"]))

    def test_active_run_appears_under_workspace_node(self) -> None:
        created = self.client.post(
            "/api/runs",
            json={
                "workspace_id": "workspace_dashpro",
                "mode": "agent",
                "summary": "git status",
            },
        ).json()
        self.client.post(f"/api/runs/{created['run_id']}/review-ready")

        payload = self._get_graph()
        node_ids = {node["node_id"] for node in payload["nodes"]}
        self.assertIn("ws_workspace_dashpro", node_ids)
        self.assertIn(f"run_{created['run_id']}", node_ids)

        edge_pairs = {(edge["source"], edge["target"]) for edge in payload["edges"]}
        self.assertIn(("core_kairo", "ws_workspace_dashpro"), edge_pairs)
        self.assertIn(("ws_workspace_dashpro", f"run_{created['run_id']}"), edge_pairs)

    def test_signal_edge_binds_to_workspace_when_workspace_node_exists(self) -> None:
        created = self.client.post(
            "/api/runs",
            json={
                "workspace_id": "workspace_dashpro",
                "mode": "agent",
                "summary": "git status",
            },
        ).json()
        self.client.post(f"/api/runs/{created['run_id']}/review-ready")

        payload = self._get_graph()
        emits = [edge for edge in payload["edges"] if edge["kind"] == "emits"]
        self.assertTrue(
            any(edge["source"] == "ws_workspace_dashpro" for edge in emits),
        )

    def test_connectors_skipped_when_watch_disconnected(self) -> None:
        with patch(
            "app.operator_brain_graph.assemble_runtime_summary",
            return_value={
                "generated_at": "2026-07-07T21:00:00Z",
                "watch": {"connected": False},
                "degraded": {"active": True, "reasons": ["watch probe failed"]},
            },
        ):
            response = self.client.get("/api/operator/brain-graph")

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertFalse(payload["watch_connected"])
        kinds = {node["kind"] for node in payload["nodes"]}
        self.assertNotIn("connector", kinds)
        core = next(node for node in payload["nodes"] if node["kind"] == "core")
        self.assertEqual("attention", core["tone"])


if __name__ == "__main__":
    unittest.main()
