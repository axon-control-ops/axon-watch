from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.workspace_source_bootstrap import (  # noqa: E402
    bootstrap_acceptance_summary,
    git_identity_issue,
    inspect_source_workspace,
    safe_stage_candidates,
    verification_commands_for_project,
)


class WorkspaceSourceBootstrapTests(unittest.TestCase):
    def test_starter_workspace_has_no_fake_node_verification(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            (root / "README.md").write_text("# Starter\n", encoding="utf-8")

            preflight = inspect_source_workspace(root)

            self.assertEqual("starter", preflight.project_type)
            self.assertEqual((), preflight.verification_commands)
            self.assertTrue(preflight.starter_workspace)

    def test_node_verification_is_derived_from_package_scripts(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            (root / "package.json").write_text(
                '{"scripts":{"test":"node --test tests/smoke.test.js","lint":"eslint ."}}\n',
                encoding="utf-8",
            )

            self.assertEqual(("npm test", "npm run lint"), verification_commands_for_project(root))

    def test_package_directory_is_reported_as_an_issue(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            (root / "README.md").write_text("# Starter\n", encoding="utf-8")
            (root / "package.json").mkdir()

            preflight = inspect_source_workspace(root)

            self.assertIn("package.json exists but is not a file", preflight.issues)
            self.assertEqual((), preflight.verification_commands)

    def test_safe_stage_candidates_are_limited_to_starter_files(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            (root / "README.md").write_text("# Starter\n", encoding="utf-8")
            (root / ".env").write_text("SECRET=yes\n", encoding="utf-8")
            (root / "src").mkdir()
            (root / "src" / "app.js").write_text("console.log('later')\n", encoding="utf-8")
            (root / "docs").mkdir()
            (root / "docs" / "health-receipt.json").write_text("{}\n", encoding="utf-8")

            self.assertEqual(["README.md"], safe_stage_candidates(root))

    def test_git_identity_issue_names_missing_config(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True)

            issue = git_identity_issue(
                root,
                lambda args, *, cwd: subprocess.CompletedProcess(args=args, returncode=1, stdout="", stderr=""),
            )

            self.assertIn("user.name", str(issue))
            self.assertIn("user.email", str(issue))

    def test_bootstrap_acceptance_summary_is_structured_and_fail_closed(self) -> None:
        summary = bootstrap_acceptance_summary(
            workspace_id="MoveIT",
            run_id="run_1",
            task_id="task_1",
            verification_command="bootstrap-contract",
            exit_code=1,
            changed_paths=["README.md"],
            commit_sha="abc123",
            branch="main",
            remote_url="https://github.com/axon-control-ops/move-it.git",
            delivery_url="https://github.com/axon-control-ops/move-it",
        )

        self.assertIn("acceptance=fail", summary)
        self.assertIn("workspace=MoveIT", summary)
        self.assertIn("exit=1", summary)
        self.assertIn("remote=https://github.com/axon-control-ops/move-it.git", summary)


if __name__ == "__main__":
    unittest.main()
