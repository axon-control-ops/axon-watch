from __future__ import annotations

import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.cli_runtime.agent_sandbox import AgentSandboxPolicy, materialize_cursor_hook_policy  # noqa: E402
from app.cli_runtime.agent_sandbox_cleanup import (  # noqa: E402
    cleanup_run_sandbox,
    prune_stale_run_sandboxes,
)
from app.cli_runtime.subprocess_runner import communicate_registered_process  # noqa: E402


class AgentSandboxCleanupTests(unittest.TestCase):
    def test_cleanup_removes_read_only_policy_and_runtime_cache(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace = root / "workspace"
            workspace.mkdir()
            (workspace / ".axon-si").mkdir()
            policy_root = root / "policies"
            material = materialize_cursor_hook_policy(
                policy=AgentSandboxPolicy(),
                run_id="run-cleanup",
                workspace_root=workspace,
                policy_root=policy_root,
            )
            cache = material.sandbox_home / ".codex" / "cache"
            cache.mkdir(parents=True)
            (cache / "large-runtime-file").write_bytes(b"x" * 1024)

            self.assertTrue(cleanup_run_sandbox("run-cleanup", policy_root=policy_root))
            self.assertFalse(material.root.exists())

    def test_prune_bounds_recent_crash_leftovers(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            now = time.time()
            for index in range(5):
                policy = root / f"run-{index}"
                policy.mkdir()
                os.utime(policy, (now - index, now - index))

            removed = prune_stale_run_sandboxes(
                policy_root=root,
                now=now,
                stale_after_seconds=3600,
                max_retained=2,
            )

            self.assertEqual(3, removed)
            self.assertEqual({"run-0", "run-1"}, {item.name for item in root.iterdir()})

    def test_cleanup_failure_is_best_effort(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace = root / "workspace"
            workspace.mkdir()
            policy_root = root / "policies"
            policy = materialize_cursor_hook_policy(
                policy=AgentSandboxPolicy(),
                run_id="run-cleanup-failure",
                workspace_root=workspace,
                policy_root=policy_root,
            )
            with patch("app.cli_runtime.agent_sandbox_cleanup.shutil.rmtree", side_effect=OSError):
                self.assertFalse(cleanup_run_sandbox("run-cleanup-failure", policy_root=policy_root))

            self.assertTrue(policy.root.exists())

    def test_process_completion_invokes_sandbox_cleanup(self) -> None:
        with (
            patch("app.cli_runtime.subprocess_runner._prepare_command", return_value=["echo"]),
            patch("app.cli_runtime.subprocess_runner.cleanup_run_sandbox") as cleanup,
        ):
            stdout, stderr, code = communicate_registered_process(
                run_id="run-process-cleanup",
                command=["echo"],
                timeout_seconds=5,
                cwd="/tmp",
                sandbox_policy=AgentSandboxPolicy(),
            )

        self.assertEqual(("\n", "", 0), (stdout, stderr, code))
        cleanup.assert_called_once_with("run-process-cleanup")

    def test_process_start_failure_invokes_sandbox_cleanup(self) -> None:
        with (
            patch("app.cli_runtime.subprocess_runner._prepare_command", return_value=["missing"]),
            patch(
                "app.cli_runtime.subprocess_runner.subprocess.Popen",
                side_effect=OSError("cannot start"),
            ),
            patch("app.cli_runtime.subprocess_runner.cleanup_run_sandbox") as cleanup,
        ):
            with self.assertRaisesRegex(OSError, "cannot start"):
                communicate_registered_process(
                    run_id="run-start-failure",
                    command=["missing"],
                    timeout_seconds=5,
                    cwd="/tmp",
                    sandbox_policy=AgentSandboxPolicy(),
                )

        cleanup.assert_called_once_with("run-start-failure")


if __name__ == "__main__":
    unittest.main()
