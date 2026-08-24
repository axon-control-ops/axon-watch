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

    def test_private_company_material_is_never_publishable(self) -> None:
        detail = publish._scan_private_company_material(
            ["website/index.html", "docs/rfq/customer-submission.pdf"]
        )
        self.assertIn("private_company_material", str(detail))
        self.assertIn("docs/rfq/customer-submission.pdf", str(detail))
        # Regression: the message used to just say "must stay local/private
        # and cannot be staged, pushed, or included in a draft PR" -- true,
        # but gave no indication this is expected/working-as-intended rather
        # than a failure to retry, nor what an operator should actually do
        # about it.
        self.assertIn("working-as-intended", str(detail))
        self.assertIn("operator must remove or relocate", str(detail))

    def test_private_path_deletion_or_rename_still_blocks_worker_delivery(self) -> None:
        detail = publish._scan_private_company_material(
            ["docs/rfq/customer-submission.pdf", "website/customer-submission.pdf"]
        )
        self.assertIn("docs/rfq/customer-submission.pdf", str(detail))

    def test_large_public_diff_is_not_mislabeled_as_private_material(self) -> None:
        paths = [f"tests/generated/test_{index}.py" for index in range(121)]
        self.assertIsNone(publish._scan_private_company_material(paths))

    def test_smart_commit_message_names_type_scope_and_outcome(self) -> None:
        message = publish._derive_commit_message(
            ["website/index.html", "website/css/site.css"],
            "Fix gallery navigation on mobile",
        )

        self.assertEqual(message, "fix(website): gallery navigation on mobile")

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
                    root, include_ignored_pathspecs=["docs/ops/receipt.md"]
                ),
            )

    def test_ignored_directory_allowance_does_not_claim_historical_files(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            self._git(root, "init")
            self._git(root, "config", "user.email", "test@example.invalid")
            self._git(root, "config", "user.name", "Axon-X test")
            (root / ".gitignore").write_text("docs/ops/\n", encoding="utf-8")
            (root / "README.md").write_text("baseline\n", encoding="utf-8")
            self._git(root, "add", ".gitignore", "README.md")
            self._git(root, "commit", "-m", "baseline")
            target = root / "docs" / "ops" / "historical-private.pdf"
            target.parent.mkdir(parents=True)
            target.write_text("private\n", encoding="utf-8")

            self.assertNotIn(
                "docs/ops/historical-private.pdf",
                list_isolation_changed_paths(
                    root, include_ignored_pathspecs=["docs/ops/"]
                ),
            )
            self.assertNotIn(
                "docs/ops/historical-private.pdf",
                list_isolation_changed_paths(
                    root, include_ignored_pathspecs=["docs/ops"]
                ),
            )


if __name__ == "__main__":
    unittest.main()
