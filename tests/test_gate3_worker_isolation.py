"""Gate 3 continuous-worker disposable isolation proofs."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

class Gate3WorkerIsolationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.bound = Path(self._tmpdir.name) / "live-project"
        self.bound.mkdir()
        # Minimal git repo for worktree/clone isolation.
        import subprocess

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
        # Import inside the test so we bind the same module object Gate 2 may have reloaded.
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

    def test_refuse_missing_isolation_root(self) -> None:
        from app.safe_improvement.isolated_executor import IsolationError
        from app.workspace_agents.worker_isolation import worker_agent_workspace

        with self.assertRaises(IsolationError):
            worker_agent_workspace(None)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
