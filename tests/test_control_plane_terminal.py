from __future__ import annotations

import json
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
from app.terminal.workspace_roots import resolve_workspace_root, workspace_roots_base  # noqa: E402


class ControlPlaneTerminalTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)
        self.workspace_tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.workspace_tempdir.cleanup)
        self.env_patch = patch.dict(
            os.environ,
            {"AXON_WATCH_WORKSPACE_ROOT": self.workspace_tempdir.name},
            clear=False,
        )
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def test_resolve_workspace_root_creates_directory_for_known_workspace(self) -> None:
        root = resolve_workspace_root("workspace_alpha")
        self.assertTrue(root.is_dir())
        self.assertEqual(root, workspace_roots_base() / "workspace_alpha")

    def test_terminal_websocket_rejects_unknown_workspace(self) -> None:
        with self.client.websocket_connect("/api/workspaces/workspace_missing/terminal") as ws:
            message = json.loads(ws.receive_text())
            self.assertEqual("error", message["type"])
            self.assertIn("workspace not found", message["message"])

    def test_terminal_websocket_runs_real_shell_command(self) -> None:
        collected: list[str] = []

        with self.client.websocket_connect("/api/workspaces/workspace_alpha/terminal") as ws:
            ready = json.loads(ws.receive_text())
            self.assertEqual("ready", ready["type"])
            self.assertEqual("workspace_alpha", ready["workspace_id"])

            ws.send_text(json.dumps({"type": "resize", "cols": 120, "rows": 30}))
            ws.send_text(json.dumps({"type": "input", "data": "echo axon-pty-smoke\n"}))

            for _ in range(40):
                payload = json.loads(ws.receive_text())
                if payload.get("type") == "output":
                    collected.append(str(payload.get("data", "")))
                if "axon-pty-smoke" in "".join(collected):
                    break

        self.assertIn("axon-pty-smoke", "".join(collected))


if __name__ == "__main__":
    unittest.main()
