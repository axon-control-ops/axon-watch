from __future__ import annotations

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
from app.workspace_files import read_workspace_file  # noqa: E402


class ControlPlaneWorkspaceFilesTests(unittest.TestCase):
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

    def test_list_workspace_files_bootstraps_readme_and_notes(self) -> None:
        response = self.client.get("/api/workspaces/workspace_alpha/files")
        self.assertEqual(200, response.status_code)
        payload = response.json()
        paths = {item["path"] for item in payload["items"]}
        self.assertIn("README.md", paths)
        self.assertIn("notes.txt", paths)

    def test_read_and_write_workspace_file_round_trip(self) -> None:
        write_response = self.client.put(
            "/api/workspaces/workspace_alpha/files/notes.txt",
            json={"content": "saved from test\n"},
        )
        self.assertEqual(200, write_response.status_code)
        self.assertTrue(write_response.json()["saved"])

        read_response = self.client.get("/api/workspaces/workspace_alpha/files/notes.txt")
        self.assertEqual(200, read_response.status_code)
        self.assertEqual("saved from test\n", read_response.json()["content"])

    def test_read_rejects_path_traversal(self) -> None:
        response = self.client.get("/api/workspaces/workspace_alpha/files/../secrets.txt")
        self.assertEqual(404, response.status_code)

    def test_read_workspace_file_reads_from_disk(self) -> None:
        on_disk = Path(self.workspace_tempdir.name) / "workspace_alpha" / "README.md"
        on_disk.parent.mkdir(parents=True, exist_ok=True)
        on_disk.write_text("# hello from disk\n", encoding="utf-8")

        payload = read_workspace_file("workspace_alpha", "README.md")
        self.assertEqual("# hello from disk\n", payload["content"])

    def test_list_workspace_files_includes_nested_paths(self) -> None:
        nested = Path(self.workspace_tempdir.name) / "workspace_alpha" / "src" / "notes.md"
        nested.parent.mkdir(parents=True, exist_ok=True)
        nested.write_text("# nested\n", encoding="utf-8")

        response = self.client.get("/api/workspaces/workspace_alpha/files")
        self.assertEqual(200, response.status_code)
        paths = {item["path"] for item in response.json()["items"]}
        self.assertIn("src/notes.md", paths)

    def test_list_workspace_files_skips_generated_and_hidden_directories(self) -> None:
        root = Path(self.workspace_tempdir.name) / "workspace_alpha"
        hidden = root / ".git" / "config"
        hidden.parent.mkdir(parents=True, exist_ok=True)
        hidden.write_text("[core]\n", encoding="utf-8")

        generated = root / "node_modules" / "left-pad" / "index.js"
        generated.parent.mkdir(parents=True, exist_ok=True)
        generated.write_text("module.exports = 1;\n", encoding="utf-8")

        source = root / "src" / "main.ts"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("export const ok = true;\n", encoding="utf-8")

        response = self.client.get("/api/workspaces/workspace_alpha/files")
        self.assertEqual(200, response.status_code)
        paths = {item["path"] for item in response.json()["items"]}
        self.assertIn("src/main.ts", paths)
        self.assertNotIn(".git/config", paths)
        self.assertNotIn("node_modules/left-pad/index.js", paths)

    def test_write_nested_workspace_file_creates_directories(self) -> None:
        write_response = self.client.put(
            "/api/workspaces/workspace_alpha/files/src/deep.txt",
            json={"content": "nested content\n"},
        )
        self.assertEqual(200, write_response.status_code)

        read_response = self.client.get("/api/workspaces/workspace_alpha/files/src/deep.txt")
        self.assertEqual(200, read_response.status_code)
        self.assertEqual("nested content\n", read_response.json()["content"])

        list_response = self.client.get("/api/workspaces/workspace_alpha/files")
        paths = {item["path"] for item in list_response.json()["items"]}
        self.assertIn("src/deep.txt", paths)

    def test_rename_workspace_file_moves_path_and_preserves_content(self) -> None:
        self.client.put(
            "/api/workspaces/workspace_alpha/files/src/deep.txt",
            json={"content": "nested content\n"},
        )

        rename_response = self.client.post(
            "/api/workspaces/workspace_alpha/files/src/deep.txt/rename",
            json={"new_path": "src/renamed.txt"},
        )
        self.assertEqual(200, rename_response.status_code)
        self.assertEqual("src/renamed.txt", rename_response.json()["path"])

        read_response = self.client.get("/api/workspaces/workspace_alpha/files/src/renamed.txt")
        self.assertEqual(200, read_response.status_code)
        self.assertEqual("nested content\n", read_response.json()["content"])

        old_response = self.client.get("/api/workspaces/workspace_alpha/files/src/deep.txt")
        self.assertEqual(404, old_response.status_code)

    def test_rename_workspace_file_rejects_existing_target(self) -> None:
        self.client.put(
            "/api/workspaces/workspace_alpha/files/src/deep.txt",
            json={"content": "nested content\n"},
        )
        self.client.put(
            "/api/workspaces/workspace_alpha/files/src/existing.txt",
            json={"content": "existing\n"},
        )

        rename_response = self.client.post(
            "/api/workspaces/workspace_alpha/files/src/deep.txt/rename",
            json={"new_path": "src/existing.txt"},
        )
        self.assertEqual(409, rename_response.status_code)


if __name__ == "__main__":
    unittest.main()
