from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.chat.command_executor import (  # noqa: E402
    classify_command,
    execute_command,
    execute_list_files,
    execute_read_file,
)


class CommandExecutorTests(unittest.TestCase):
    def test_classify_command_recognizes_supported_intents(self) -> None:
        self.assertEqual(classify_command("curl -s http://127.0.0.1:8787/api/health"), "health_probe")
        self.assertEqual(classify_command("list files"), "list_files")
        self.assertEqual(classify_command("read README.md"), "read_file")
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
            result = execute_command(workspace_id="workspace_alpha", content="check health")

        self.assertTrue(result.success)
        self.assertIn("control-plane", result.output)


if __name__ == "__main__":
    unittest.main()
