from __future__ import annotations

import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.host_context.policy import classify_action, evaluate_action_request  # noqa: E402
from app.main import app  # noqa: E402
from app.persistence import run_store  # noqa: E402


class HostContextApiTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def test_policy_tiers(self) -> None:
        self.assertEqual("auto", classify_action("open.path", path="/home/edp/Documents/a.pdf"))
        self.assertEqual("confirm", classify_action("open.path", path="/home/edp/.ssh/id_rsa"))
        self.assertEqual("deny", classify_action("shell.execute"))
        decision = evaluate_action_request(action="clipboard.read")
        self.assertFalse(decision["allowed"])
        self.assertTrue(decision["requires_approval"])

    def test_snapshot_artifacts_actions_and_replay(self) -> None:
        snap = self.client.post(
            "/api/host/bridge/snapshot",
            json={
                "device_id": "device_test_1",
                "snapshot": {
                    "host": {"hostname": "kali", "platform": "linux", "user": "edp"},
                    "capabilities": ["open.path", "health.snapshot"],
                    "windows": [{"window_id": "1", "title": "VAXON", "app": "vaxon", "focused": True}],
                },
                "events": [
                    {
                        "kind": "host.focus",
                        "title": "Focused VAXON",
                        "detail": "main window",
                    }
                ],
            },
        )
        self.assertEqual(200, snap.status_code)
        self.assertTrue(snap.json()["accepted"])

        caps = self.client.get("/api/host/capabilities")
        self.assertEqual(200, caps.status_code)
        self.assertEqual("desktop", caps.json()["runtime"])
        self.assertEqual(1, len(caps.json()["devices"]))

        arts = self.client.post(
            "/api/host/artifacts",
            json={
                "device_id": "device_test_1",
                "items": [
                    {
                        "artifact_id": "hart_doc_1",
                        "path": "/home/edp/Documents/plan.md",
                        "title": "plan.md",
                        "kind": "file",
                        "origin": "Documents",
                    }
                ],
            },
        )
        self.assertEqual(200, arts.status_code)
        self.assertEqual(1, arts.json()["count"])

        listed = self.client.get("/api/host/artifacts", params={"query": "plan"})
        self.assertEqual(1, listed.json()["count"])

        action = self.client.post(
            "/api/host/actions/request",
            json={
                "device_id": "device_test_1",
                "action": "open.path",
                "path": "/home/edp/Documents/plan.md",
                "command_id": "cmd_open_1",
            },
        )
        self.assertEqual(200, action.status_code)
        payload = action.json()
        self.assertTrue(payload["accepted"])
        self.assertEqual("queued", payload["receipt"]["status"])

        replay = self.client.post(
            "/api/host/actions/request",
            json={
                "device_id": "device_test_1",
                "action": "open.path",
                "path": "/home/edp/Documents/plan.md",
                "command_id": "cmd_open_1",
            },
        )
        self.assertFalse(replay.json()["accepted"])
        self.assertTrue(replay.json()["replay"])

        denied = self.client.post(
            "/api/host/actions/request",
            json={
                "device_id": "device_test_1",
                "action": "shell.execute",
                "command_id": "cmd_shell_1",
            },
        )
        self.assertFalse(denied.json()["accepted"])
        self.assertEqual("denied", denied.json()["receipt"]["status"])

        from app.host_context import store as host_store

        pruned = host_store.prune_expired(retention_days=14)
        self.assertIn("events_deleted", pruned)

        pause = self.client.post("/api/host/privacy/pause", json={"paused": True})
        self.assertTrue(pause.json()["awareness_paused"])
        blocked = self.client.post(
            "/api/host/bridge/snapshot",
            json={"device_id": "device_test_1", "snapshot": {"host": {"hostname": "kali"}}},
        )
        self.assertFalse(blocked.json()["accepted"])

    def test_brain_graph_includes_host_nodes(self) -> None:
        self.client.post(
            "/api/host/bridge/snapshot",
            json={
                "device_id": "device_graph_1",
                "snapshot": {"host": {"hostname": "workstation", "platform": "linux"}},
            },
        )
        self.client.post(
            "/api/host/artifacts",
            json={
                "device_id": "device_graph_1",
                "items": [
                    {
                        "artifact_id": "hart_img_1",
                        "title": "shot.png",
                        "path": "/tmp/shot.png",
                        "kind": "image",
                    }
                ],
            },
        )
        response = self.client.get("/api/operator/brain-graph")
        self.assertEqual(200, response.status_code)
        kinds = {node["kind"] for node in response.json()["nodes"]}
        self.assertIn("device", kinds)
        self.assertIn("media", kinds)


if __name__ == "__main__":
    unittest.main()
