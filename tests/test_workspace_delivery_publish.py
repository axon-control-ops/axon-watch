from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.workspace_delivery import publish  # noqa: E402
from app.workspace_delivery.publish import list_isolation_changed_paths  # noqa: E402


class WorkspaceDeliveryPublishTests(unittest.TestCase):
    def test_publish_stages_only_the_audited_paths(self) -> None:
        calls: list[list[str]] = []

        def fake_run(args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            calls.append(args)
            return subprocess.CompletedProcess(args, 0, "", "")

        with patch("app.workspace_delivery.publish._run", side_effect=fake_run):
            result = publish._stage_isolation_paths(
                Path("/tmp/isolated-worker"),
                ["services/control-plane/app/api.py", "tests/test_api.py"],
            )

        self.assertEqual(0, result.returncode)
        self.assertEqual(
            [
                "git",
                "add",
                "-f",
                "--",
                "services/control-plane/app/api.py",
                "tests/test_api.py",
            ],
            calls[0],
        )

    def _git(self, root: Path, *args: str) -> None:
        result = subprocess.run(
            ["git", *args], cwd=root, capture_output=True, text=True, check=False
        )
        self.assertEqual(0, result.returncode, result.stderr)

    def test_explicitly_scoped_ignored_work_is_a_delivery_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            self._git(root, "init")
            self._git(root, "config", "user.email", "test@example.invalid")
            self._git(root, "config", "user.name", "Axon-X test")
            (root / ".gitignore").write_text("docs/ops/\n", encoding="utf-8")
            (root / "README.md").write_text("baseline\n", encoding="utf-8")
            self._git(root, "add", ".gitignore", "README.md")
            self._git(root, "commit", "-m", "baseline")
            target = root / "docs" / "ops" / "receipt.md"
            target.parent.mkdir(parents=True)
            target.write_text("verified\n", encoding="utf-8")

            self.assertNotIn("docs/ops/receipt.md", list_isolation_changed_paths(root))
            self.assertIn(
                "docs/ops/receipt.md",
                list_isolation_changed_paths(
                    root, include_ignored_pathspecs=["docs/ops"]
                ),
            )


if __name__ == "__main__":
    unittest.main()
