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

    def test_stale_binding_does_not_hide_valid_workspaces(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            project_root = Path(tempdir) / "valid"
            project_root.mkdir()
            bindings_file = Path(tempdir) / "bindings.json"
            bindings_file.write_text(json.dumps({"bindings": {
                "workspace_valid": {"project_root": str(project_root)},
                "workspace_stale": {"project_root": str(Path(tempdir) / "gone")},
            }}), encoding="utf-8")
            with patch.dict(os.environ, {"AXON_WATCH_PROJECT_ROOT_ALLOWLIST": str(tempdir)}, clear=False):
                bindings = load_workspace_project_bindings(bindings_file)
            self.assertIn("workspace_valid", bindings)
            self.assertNotIn("workspace_stale", bindings)

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


    def test_single_lookup_is_not_broken_by_an_unrelated_bad_binding(self) -> None:
        """Regression guard for a real, recurring outage.

        get_workspace_record (and therefore build_company_roster, sandbox
        status, and live-service policy widening -- three separate incidents
        in one session) used to call the *full* registry loader just to look
        up one workspace. One misconfigured workspace anywhere in the
        bindings file broke every *other* workspace's lookup, because that
        loader deliberately fails closed for the whole map. A single-workspace
        lookup must resolve or fail on its own binding only.
        """
        with tempfile.TemporaryDirectory() as tempdir:
            good_root = Path(tempdir) / "good"
            good_root.mkdir()
            bad_root = Path(tempdir) / "bad"
            bad_root.mkdir()
            bindings_file = Path(tempdir) / "bindings.json"
            bindings_file.write_text(
                json.dumps(
                    {
                        "bindings": {
                            "workspace_good": {"project_root": str(good_root)},
                            "workspace_bad": {"project_root": str(bad_root)},
                        }
                    }
                ),
                encoding="utf-8",
            )
            with patch.dict(
                os.environ,
                {"AXON_WATCH_PROJECT_ROOT_ALLOWLIST": str(good_root)},
                clear=False,
            ), patch(
                "app.workspace_project_bindings.default_bindings_file",
                return_value=bindings_file,
            ):
                # The full registry loader is untouched: it still fails closed
                # for the whole map, exactly as test_rejects_project_root_outside_allowlist
                # above requires.
                with self.assertRaises(WorkspaceBindingError):
                    load_workspace_project_bindings(bindings_file)

                # workspace_bad's own violation is still enforced individually.
                with self.assertRaises(WorkspaceBindingError):
                    get_workspace_project_binding("workspace_bad")

                # workspace_good must resolve fine -- this is the exact case
                # that broke get_workspace_record for every unrelated workspace.
                binding = get_workspace_project_binding("workspace_good")
                self.assertIsNotNone(binding)
                assert binding is not None
                self.assertEqual(binding.project_root, good_root.resolve())


if __name__ == "__main__":
    unittest.main()
