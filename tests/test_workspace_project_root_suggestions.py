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

from app.workspace_project_root_suggestions import suggest_project_roots  # noqa: E402


class WorkspaceProjectRootSuggestionsTests(unittest.TestCase):
    def _fixture(self, tempdir: str) -> None:
        client_dir = Path(tempdir) / "client"
        client_dir.mkdir()
        (client_dir / "existing_project").mkdir()
        (client_dir / "new_project").mkdir()
        (client_dir / "other_thing").mkdir()
        bindings_file = Path(tempdir) / "bindings.json"
        bindings_file.write_text(
            json.dumps(
                {
                    "bindings": {
                        "workspace_existing": {
                            "project_root": str(client_dir / "existing_project"),
                            "display_name": "Existing project",
                        }
                    }
                }
            ),
            encoding="utf-8",
        )
        self._env_patch = patch.dict(
            os.environ,
            {
                "AXON_WATCH_WORKSPACE_BINDINGS_FILE": str(bindings_file),
                "AXON_WATCH_PROJECT_ROOT_ALLOWLIST": tempdir,
            },
            clear=False,
        )
        self._env_patch.start()
        self.addCleanup(self._env_patch.stop)

    def test_suggests_unregistered_siblings_matching_the_query(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            self._fixture(tempdir)
            results = suggest_project_roots("new")
            labels = [item["label"] for item in results]
            self.assertEqual(["new_project"], labels)

    def test_never_suggests_an_already_registered_project_root(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            self._fixture(tempdir)
            results = suggest_project_roots("existing")
            self.assertEqual([], results)

    def test_empty_query_returns_unranked_unregistered_siblings(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            self._fixture(tempdir)
            results = suggest_project_roots("")
            labels = {item["label"] for item in results}
            self.assertEqual({"new_project", "other_thing"}, labels)

    def test_no_match_returns_empty_list(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            self._fixture(tempdir)
            results = suggest_project_roots("no-such-token-anywhere")
            self.assertEqual([], results)

    def test_candidates_outside_the_allowlist_are_never_suggested(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir, tempfile.TemporaryDirectory() as outside:
            self._fixture(tempdir)
            # A binding whose parent directory sits outside the allowlist must
            # never cause that outside directory's siblings to be scanned/leaked.
            outside_project = Path(outside) / "outside_project"
            outside_project.mkdir()
            (Path(outside) / "outside_sibling").mkdir()
            bindings_file = Path(os.environ["AXON_WATCH_WORKSPACE_BINDINGS_FILE"])
            payload = json.loads(bindings_file.read_text(encoding="utf-8"))
            payload["bindings"]["workspace_outside"] = {
                "project_root": str(outside_project),
            }
            bindings_file.write_text(json.dumps(payload), encoding="utf-8")
            with patch.dict(
                os.environ,
                {"AXON_WATCH_PROJECT_ROOT_ALLOWLIST": tempdir},
                clear=False,
            ):
                results = suggest_project_roots("outside")
            self.assertEqual([], results)


if __name__ == "__main__":
    unittest.main()
