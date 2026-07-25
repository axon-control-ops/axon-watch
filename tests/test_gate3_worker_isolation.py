"""Gate 3 continuous-worker disposable isolation proofs."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))


def _git_status_porcelain(cwd: Path) -> str:
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def _branch_exists(cwd: Path, branch: str) -> bool:
    result = subprocess.run(
        ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


class Gate3WorkerIsolationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.bound = Path(self._tmpdir.name) / "live-project"
        self.bound.mkdir()
        subprocess.run(["git", "init"], cwd=self.bound, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "gate3@example.com"],
            cwd=self.bound,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Gate3"],
            cwd=self.bound,
            check=True,
            capture_output=True,
        )
        (self.bound / "README.md").write_text("live\n", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=self.bound, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "init"],
            cwd=self.bound,
            check=True,
            capture_output=True,
        )

    def test_worker_isolation_is_not_live_checkout_and_cleans_up(self) -> None:
        from app.workspace_agents import worker_isolation as wi

        with patch.object(wi, "resolve_workspace_root", return_value=self.bound):
            isolation = wi.create_worker_isolation(workspace_id="workspace_demo", run_id="run_gate3")
            agent_root = wi.worker_agent_workspace(isolation)
            self.assertTrue(agent_root.is_dir())
            self.assertNotEqual(agent_root.resolve(), self.bound.resolve())
            self.assertTrue((agent_root / "README.md").is_file())
            # Mutate only the disposable tree.
            (agent_root / "worker-only.txt").write_text("isolated\n", encoding="utf-8")
            self.assertFalse((self.bound / "worker-only.txt").exists())
            cleanup = wi.cleanup_worker_isolation(isolation)
            self.assertTrue(cleanup.get("cleaned") or cleanup.get("removed"))
            self.assertFalse(agent_root.exists())

    def test_named_worker_branch_created_and_deleted_on_cleanup(self) -> None:
        from app.safe_improvement import isolated_executor as iso
        from app.workspace_agents import worker_isolation as wi

        expected_branch = iso.worker_branch_name("run_named_branch")
        with patch.object(wi, "resolve_workspace_root", return_value=self.bound):
            isolation = wi.create_worker_isolation(
                workspace_id="workspace_demo",
                run_id="run_named_branch",
            )
            meta = iso.read_baseline_metadata(isolation)
            self.assertEqual(meta.get("isolation_kind"), "worktree")
            self.assertEqual(meta.get("worker_branch"), expected_branch)
            self.assertTrue(_branch_exists(self.bound, expected_branch))
            summary = wi.isolation_receipt_summary(isolation)
            self.assertIn(expected_branch, summary)

            cleanup = wi.cleanup_worker_isolation(isolation)
            self.assertTrue(cleanup.get("cleaned") or cleanup.get("removed"))
            self.assertEqual(cleanup.get("worker_branch"), expected_branch)
            self.assertTrue(cleanup.get("branch_deleted"))
            self.assertFalse(_branch_exists(self.bound, expected_branch))

    def test_concurrent_isolations_leave_live_root_untouched(self) -> None:
        from app.workspace_agents import worker_isolation as wi

        before = _git_status_porcelain(self.bound)
        with patch.object(wi, "resolve_workspace_root", return_value=self.bound):
            a = wi.create_worker_isolation(workspace_id="workspace_demo", run_id="run_conc_a")
            b = wi.create_worker_isolation(workspace_id="workspace_demo", run_id="run_conc_b")
            root_a = wi.worker_agent_workspace(a)
            root_b = wi.worker_agent_workspace(b)
            self.assertNotEqual(root_a.resolve(), root_b.resolve())
            self.assertNotEqual(root_a.resolve(), self.bound.resolve())
            self.assertNotEqual(root_b.resolve(), self.bound.resolve())

            (root_a / "from-a.txt").write_text("a\n", encoding="utf-8")
            (root_b / "from-b.txt").write_text("b\n", encoding="utf-8")
            self.assertFalse((self.bound / "from-a.txt").exists())
            self.assertFalse((self.bound / "from-b.txt").exists())
            self.assertFalse((root_a / "from-b.txt").exists())
            self.assertFalse((root_b / "from-a.txt").exists())

            mid = _git_status_porcelain(self.bound)
            self.assertEqual(before, mid)

            cleanup_a = wi.cleanup_worker_isolation(a)
            cleanup_b = wi.cleanup_worker_isolation(b)
            self.assertTrue(cleanup_a.get("cleaned") or cleanup_a.get("removed"))
            self.assertTrue(cleanup_b.get("cleaned") or cleanup_b.get("removed"))

        after = _git_status_porcelain(self.bound)
        self.assertEqual(before, after)

    def test_refuse_path_outside_disposable_root(self) -> None:
        from app.safe_improvement import isolated_executor as iso
        from app.workspace_agents import worker_isolation as wi

        with patch.object(wi, "resolve_workspace_root", return_value=self.bound):
            isolation = wi.create_worker_isolation(
                workspace_id="workspace_demo",
                run_id="run_path_forbid",
            )
            try:
                inside = iso.resolve_path_within_isolation(isolation, "notes.txt")
                self.assertTrue(str(inside).startswith(str(isolation.resolve())))
                with self.assertRaises(iso.IsolationError):
                    iso.resolve_path_within_isolation(isolation, "../escape.txt")
                with self.assertRaises(iso.IsolationError):
                    iso.assert_mutation_within_isolation(
                        isolation,
                        self.bound / "README.md",
                    )
            finally:
                wi.cleanup_worker_isolation(isolation)

    def test_refuse_missing_isolation_root(self) -> None:
        from app.safe_improvement.isolated_executor import IsolationError
        from app.workspace_agents.worker_isolation import worker_agent_workspace

        with self.assertRaises(IsolationError):
            worker_agent_workspace(None)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
