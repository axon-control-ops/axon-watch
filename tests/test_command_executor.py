from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.chat.command_executor import (  # noqa: E402
    classify_command,
    execute_command,
    execute_git_status,
    execute_list_files,
    execute_read_file,
    execute_resume_from_review,
)


class CommandExecutorTests(unittest.TestCase):
    def setUp(self) -> None:
        from app.persistence import run_store

        isolate_control_plane_db(self, run_store)

    def test_classify_command_recognizes_supported_intents(self) -> None:
        self.assertEqual(classify_command("curl -s http://127.0.0.1:8787/api/health"), "health_probe")
        self.assertEqual(classify_command("list files"), "list_files")
        self.assertEqual(classify_command("read README.md"), "read_file")
        self.assertEqual(classify_command("git status"), "git_status")
        self.assertEqual(classify_command("resume from review"), "resume_from_review")
        self.assertEqual(classify_command("do something exotic"), "unsupported")

    def test_execute_read_file_returns_workspace_content(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir) / "workspace_alpha"
            root.mkdir()
            (root / "README.md").write_text("# hello executor\n", encoding="utf-8")

            with patch.dict("os.environ", {"AXON_WATCH_WORKSPACE_ROOT": tempdir}, clear=False):
                result = execute_read_file("workspace_alpha", "read README.md")

            self.assertTrue(result.success)
            self.assertEqual("read_file", result.intent)
            self.assertIn("hello executor", result.output)

    def test_execute_list_files_returns_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir) / "workspace_alpha"
            root.mkdir()
            (root / "notes.txt").write_text("notes\n", encoding="utf-8")

            with patch.dict("os.environ", {"AXON_WATCH_WORKSPACE_ROOT": tempdir}, clear=False):
                result = execute_list_files("workspace_alpha")

            self.assertTrue(result.success)
            self.assertIn("notes.txt", result.output)

    def test_execute_command_unsupported_includes_hints(self) -> None:
        result = execute_command(workspace_id="workspace_alpha", content="deploy prod now")
        self.assertFalse(result.success)
        self.assertEqual("unsupported", result.intent)
        self.assertIn("Supported commands", result.output)

    def test_execute_health_probe_parses_json(self) -> None:
        payload = {"service": "control-plane", "status": "ok"}

        class FakeResponse:
            def read(self) -> bytes:
                return json.dumps(payload).encode()

            def __enter__(self):
                return self

            def __exit__(self, *args: object) -> None:
                return None

        with patch("app.chat.command_executor.urlopen", return_value=FakeResponse()):
            result = execute_command(workspace_id="workspace_alpha", content="health")

        self.assertTrue(result.success)
        self.assertIn("control-plane", result.output)

    def test_execute_git_status_returns_repo_state(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir) / "workspace_alpha"
            root.mkdir()
            subprocess = __import__("subprocess")
            subprocess.run(["git", "init"], cwd=root, capture_output=True, check=False)

            with patch.dict("os.environ", {"AXON_WATCH_WORKSPACE_ROOT": tempdir}, clear=False):
                result = execute_git_status("workspace_alpha")

            self.assertEqual("git_status", result.intent)
            self.assertTrue(result.success)
            self.assertTrue(result.output.strip())

    def test_dashpro_ota_shortcut_requires_dashpro_workspace(self) -> None:
        result = execute_command(workspace_id="workspace_alpha", content="ota canary")
        self.assertFalse(result.success)
        self.assertIn("workspace_dashpro", result.output)

    def test_dashpro_ota_shortcut_dispatches_canary_command(self) -> None:
        with patch(
            "app.chat.command_executor.execute_shell_command",
            return_value=(True, "published to operator-canary", "exit 0"),
        ) as mocked:
            result = execute_command(workspace_id="workspace_dashpro", content="ota canary")

        self.assertTrue(result.success)
        self.assertEqual("shell_command", result.intent)
        self.assertIn("operator-canary", result.output)
        mocked.assert_called_once_with(
            workspace_id="workspace_dashpro",
            content="run npm run ota:canary",
        )

    def test_production_ota_is_blocked(self) -> None:
        result = execute_command(
            workspace_id="workspace_dashpro",
            content="run npm run ota:production",
        )
        self.assertFalse(result.success)
        self.assertIn("Production OTA is blocked", result.output)

    def test_execute_resume_from_review_resumes_primary_review_ready_run(self) -> None:
        from app.main import app  # noqa: WPS433
        from fastapi.testclient import TestClient

        client = TestClient(app)
        self.addCleanup(client.close)
        created = client.post(
            "/api/runs",
            json={
                "workspace_id": "workspace_alpha",
                "mode": "agent",
                "summary": "Review resume command target",
            },
        ).json()
        client.post(f"/api/runs/{created['run_id']}/review-ready")

        result = execute_resume_from_review("workspace_alpha")

        self.assertTrue(result.success)
        self.assertEqual(created["run_id"], result.run_id)
        self.assertEqual("executing", client.get(f"/api/runs/{created['run_id']}").json()["phase"])

    def test_execute_resume_from_review_auto_completes_one_shot_git_status(self) -> None:
        from app.main import app  # noqa: WPS433
        from fastapi.testclient import TestClient

        client = TestClient(app)
        self.addCleanup(client.close)
        created = client.post(
            "/api/runs",
            json={
                "workspace_id": "workspace_alpha",
                "mode": "agent",
                "summary": "git status",
            },
        ).json()
        client.post(f"/api/runs/{created['run_id']}/review-ready")

        result = execute_resume_from_review("workspace_alpha")

        self.assertTrue(result.success)
        self.assertEqual(created["run_id"], result.run_id)
        self.assertIn("One-shot command", result.output)
        self.assertEqual("completed", client.get(f"/api/runs/{created['run_id']}").json()["phase"])


if __name__ == "__main__":
    unittest.main()
