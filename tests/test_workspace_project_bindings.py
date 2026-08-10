from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.workspace_project_bindings import (  # noqa: E402
    WorkspaceBindingError,
    get_workspace_project_binding,
    load_workspace_project_bindings,
    project_root_allowlist,
)


class WorkspaceProjectBindingsTests(unittest.TestCase):
    def test_missing_bindings_file_returns_empty_map(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            missing = Path(tempdir) / "missing-bindings.json"
            self.assertEqual(load_workspace_project_bindings(missing), {})

    def test_loads_binding_with_relative_project_root(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            project_root = Path(tempdir) / "project"
            project_root.mkdir()
            bindings_file = Path(tempdir) / "bindings.json"
            bindings_file.write_text(
                json.dumps(
                    {
                        "bindings": {
                            "workspace_demo": {
                                "project_root": str(project_root),
                                "display_name": "Demo project",
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            with patch.dict(
                os.environ,
                {
                    "AXON_WATCH_PROJECT_ROOT_ALLOWLIST": str(tempdir),
                },
                clear=False,
            ):
                bindings = load_workspace_project_bindings(bindings_file)

            self.assertIn("workspace_demo", bindings)
            binding = bindings["workspace_demo"]
            self.assertEqual(binding.project_root.resolve(), project_root.resolve())
            self.assertEqual(binding.display_name, "Demo project")

    def test_rejects_project_root_outside_allowlist(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            project_root = Path(tempdir) / "project"
            project_root.mkdir()
            bindings_file = Path(tempdir) / "bindings.json"
            bindings_file.write_text(
                json.dumps(
                    {
                        "bindings": {
                            "workspace_blocked": {
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
                    "AXON_WATCH_PROJECT_ROOT_ALLOWLIST": "/tmp/axon-watch-allowlist-only",
                },
                clear=False,
            ):
                with self.assertRaises(WorkspaceBindingError):
                    load_workspace_project_bindings(bindings_file)

    def test_default_allowlist_includes_run_media_user_mount(self) -> None:
        with patch("app.workspace_project_bindings._repo_root") as repo_root:
            repo_root.return_value = Path(
                "/run/media/vaxon/axon-data/repos/axon-nvme/repos/axon-watch"
            )

            self.assertIn(Path("/run/media/vaxon"), project_root_allowlist())

    def test_get_workspace_project_binding_returns_none_for_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            bindings_file = Path(tempdir) / "bindings.json"
            bindings_file.write_text(json.dumps({"bindings": {}}), encoding="utf-8")
            with patch.dict(
                os.environ,
                {"AXON_WATCH_WORKSPACE_BINDINGS_FILE": str(bindings_file)},
                clear=False,
            ):
                self.assertIsNone(get_workspace_project_binding("workspace_missing"))

    def test_upsert_workspace_project_binding_persists_and_reloads(self) -> None:
        from app.workspace_project_bindings import upsert_workspace_project_binding

        with tempfile.TemporaryDirectory() as tempdir:
            project_root = Path(tempdir) / "project"
            project_root.mkdir()
            bindings_file = Path(tempdir) / "bindings.json"
            with patch.dict(
                os.environ,
                {
                    "AXON_WATCH_PROJECT_ROOT_ALLOWLIST": str(tempdir),
                    "AXON_WATCH_WORKSPACE_BINDINGS_FILE": str(bindings_file),
                },
                clear=False,
            ):
                created = upsert_workspace_project_binding(
                    workspace_id="workspace_new",
                    project_root=str(project_root),
                    display_name="New Project",
                    bindings_file=bindings_file,
                )
                self.assertEqual(created.workspace_id, "workspace_new")
                reloaded = load_workspace_project_bindings(bindings_file)
                self.assertIn("workspace_new", reloaded)
                self.assertEqual(reloaded["workspace_new"].display_name, "New Project")


if __name__ == "__main__":
    unittest.main()
