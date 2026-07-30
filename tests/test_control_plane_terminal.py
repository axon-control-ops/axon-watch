from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.main import app  # noqa: E402
from app.persistence import run_store  # noqa: E402
from app.terminal.session_registry import reset_registry  # noqa: E402
from app.terminal.session_runtime import reset_runtimes  # noqa: E402
from app.terminal.workspace_roots import resolve_workspace_root, workspace_roots_base  # noqa: E402


class ControlPlaneTerminalTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)
        reset_registry()
        reset_runtimes()
        self.addCleanup(reset_registry)
        self.addCleanup(reset_runtimes)
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

    def test_resolve_workspace_root_uses_project_binding_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            project_root = Path(tempdir) / "bound-project"
            project_root.mkdir()
            bindings_file = Path(tempdir) / "bindings.json"
            bindings_file.write_text(
                json.dumps(
                    {
                        "bindings": {
                            "workspace_bound_terminal": {
                                "project_root": str(project_root),
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            with patch.dict(
                os.environ,
                {
                    "AXON_WATCH_WORKSPACE_BINDINGS_FILE": str(bindings_file),
                    "AXON_WATCH_PROJECT_ROOT_ALLOWLIST": str(tempdir),
                },
                clear=False,
            ):
                root = resolve_workspace_root("workspace_bound_terminal")

            self.assertEqual(root.resolve(), project_root.resolve())
            isolated_candidate = workspace_roots_base() / "workspace_bound_terminal"
            self.assertFalse(isolated_candidate.exists())

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

    def test_terminal_session_persists_shell_state_across_reconnects(self) -> None:
        session_id = "terminal-reconnect-smoke"

        with self.client.websocket_connect(
            f"/api/workspaces/workspace_alpha/terminal?session_id={session_id}"
        ) as ws:
            ws.receive_text()
            ws.send_text(json.dumps({"type": "input", "data": "export AXON_TERM_PERSIST=sticky\n"}))

        collected: list[str] = []
        with self.client.websocket_connect(
            f"/api/workspaces/workspace_alpha/terminal?session_id={session_id}"
        ) as ws:
            ws.receive_text()
            ws.send_text(json.dumps({"type": "input", "data": "echo $AXON_TERM_PERSIST\n"}))
            for _ in range(50):
                payload = json.loads(ws.receive_text())
                if payload.get("type") == "output":
                    collected.append(str(payload.get("data", "")))
                if "sticky" in "".join(collected):
                    break

        self.assertIn("sticky", "".join(collected))

    def test_agent_terminal_ignores_operator_input(self) -> None:
        fake_pty = Mock()
        fake_pty.attach_reader.side_effect = lambda loop, on_output, on_closed: None
        fake_pty.detach_reader.side_effect = lambda loop: None
        fake_runtime = Mock()
        fake_runtime.pty = fake_pty

        with patch("app.terminal.session_handler.ensure_runtime", return_value=fake_runtime):
            with self.client.websocket_connect(
                "/api/workspaces/workspace_alpha/terminal?session_id=terminal-agent-test&role=agent"
            ) as ws:
                ready = json.loads(ws.receive_text())
                self.assertEqual("agent", ready["role"])
                ws.send_text(json.dumps({"type": "input", "data": "echo should-not-run\n"}))
                ws.send_text(json.dumps({"type": "resize", "cols": 120, "rows": 30}))
                ws.send_text(json.dumps({"type": "close"}))

        fake_pty.write.assert_not_called()
        fake_pty.resize.assert_called_once_with(120, 30)

    def test_agent_terminal_runs_explicit_programmatic_command(self) -> None:
        fake_pty = Mock()
        fake_pty.attach_reader.side_effect = lambda loop, on_output, on_closed: None
        fake_pty.detach_reader.side_effect = lambda loop: None
        fake_runtime = Mock()
        fake_runtime.pty = fake_pty

        with patch("app.terminal.session_handler.ensure_runtime", return_value=fake_runtime):
            with self.client.websocket_connect(
                "/api/workspaces/workspace_alpha/terminal?session_id=terminal-agent-test&role=agent"
            ) as ws:
                ready = json.loads(ws.receive_text())
                self.assertEqual("agent", ready["role"])
                ws.send_text(
                    json.dumps(
                        {
                            "type": "run_command",
                            "command": "npm run ota:canary",
                        }
                    )
                )
                ws.send_text(json.dumps({"type": "close"}))

        fake_pty.write.assert_called_once_with(b"npm run ota:canary\n")


if __name__ == "__main__":
    unittest.main()
