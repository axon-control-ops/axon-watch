from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.chat.lane_b_git_dispatch import try_lane_b_git_commit_dispatch  # noqa: E402
from app.chat.workspace_git import git_commit, git_status  # noqa: E402


class WorkspaceGitTests(unittest.TestCase):
    def test_git_status_in_temp_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir) / "workspace_alpha"
            root.mkdir()
            subprocess.run(["git", "init"], cwd=root, capture_output=True, check=False)
            (root / "notes.txt").write_text("hello\n", encoding="utf-8")

            with patch.dict("os.environ", {"AXON_WATCH_WORKSPACE_ROOT": tempdir}, clear=False):
                result = git_status("workspace_alpha")

            self.assertTrue(result.success)
            self.assertIn("notes.txt", result.output)

    def test_git_commit_stages_and_commits(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir) / "workspace_alpha"
            root.mkdir()
            subprocess.run(["git", "init"], cwd=root, capture_output=True, check=False)
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=root,
                capture_output=True,
                check=False,
            )
            subprocess.run(
                ["git", "config", "user.name", "Axon Test"],
                cwd=root,
                capture_output=True,
                check=False,
            )
            (root / "notes.txt").write_text("hello\n", encoding="utf-8")
            subprocess.run(["git", "add", "notes.txt"], cwd=root, capture_output=True, check=False)

            with patch.dict("os.environ", {"AXON_WATCH_WORKSPACE_ROOT": tempdir}, clear=False):
                result = git_commit("workspace_alpha", "Add notes")

            self.assertTrue(result.success)
            self.assertIn("Add notes", result.output)


class LaneBGitDispatchTests(unittest.TestCase):
    def test_skips_without_full_access(self) -> None:
        payload = try_lane_b_git_commit_dispatch(
            workspace_id="workspace_alpha",
            user_prompt="commit these changes",
            execution_access="consultative",
        )
        self.assertIsNone(payload)

    def test_skips_without_commit_intent(self) -> None:
        payload = try_lane_b_git_commit_dispatch(
            workspace_id="workspace_alpha",
            user_prompt="explain README.md",
            execution_access="full",
        )
        self.assertIsNone(payload)

    def test_full_access_commit_dispatch(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir) / "workspace_alpha"
            root.mkdir()
            subprocess.run(["git", "init"], cwd=root, capture_output=True, check=False)
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=root,
                capture_output=True,
                check=False,
            )
            subprocess.run(
                ["git", "config", "user.name", "Axon Test"],
                cwd=root,
                capture_output=True,
                check=False,
            )
            (root / "notes.txt").write_text("hello\n", encoding="utf-8")

            with patch.dict("os.environ", {"AXON_WATCH_WORKSPACE_ROOT": tempdir}, clear=False):
                payload = try_lane_b_git_commit_dispatch(
                    workspace_id="workspace_alpha",
                    user_prompt='commit these changes with message "Ship notes"',
                    execution_access="full",
                )

            self.assertIsNotNone(payload)
            assert payload is not None
            self.assertTrue(payload["dispatched"])
            self.assertIn("Ship notes", str(payload["content"]))

    def test_commit_and_push_dispatch_reports_push(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            remote = Path(tempdir) / "remote.git"
            subprocess.run(
                ["git", "init", "--bare", str(remote)], capture_output=True, check=False
            )
            root = Path(tempdir) / "workspace_alpha"
            root.mkdir()
            subprocess.run(["git", "init", "-b", "main"], cwd=root, capture_output=True, check=False)
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=root,
                capture_output=True,
                check=False,
            )
            subprocess.run(
                ["git", "config", "user.name", "Axon Test"],
                cwd=root,
                capture_output=True,
                check=False,
            )
            subprocess.run(
                ["git", "remote", "add", "origin", str(remote)],
                cwd=root,
                capture_output=True,
                check=False,
            )
            (root / "notes.txt").write_text("hello\n", encoding="utf-8")
            subprocess.run(["git", "add", "-A"], cwd=root, capture_output=True, check=False)
            subprocess.run(
                ["git", "commit", "-m", "seed"], cwd=root, capture_output=True, check=False
            )
            subprocess.run(
                ["git", "push", "-u", "origin", "main"],
                cwd=root,
                capture_output=True,
                check=False,
            )
            (root / "notes.txt").write_text("hello again\n", encoding="utf-8")

            with patch.dict("os.environ", {"AXON_WATCH_WORKSPACE_ROOT": tempdir}, clear=False):
                payload = try_lane_b_git_commit_dispatch(
                    workspace_id="workspace_alpha",
                    user_prompt='commit and push with message "Ship again"',
                    execution_access="full",
                )

            self.assertIsNotNone(payload)
            assert payload is not None
            self.assertTrue(payload["dispatched"])
            self.assertIn("Pushed to the remote", str(payload["content"]))


if __name__ == "__main__":
    unittest.main()
