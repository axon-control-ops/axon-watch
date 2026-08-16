"""Full Auto composer Sandbox lifecycle coverage."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from app.cli_runtime import composer_sandbox
from app.cli_runtime.composer_execution_policy import resolve_composer_execution_policy
from app.persistence import composer_sandbox_store


class ComposerSandboxPolicyV2Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.project = base / "project"
        self.project.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=self.project, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.project, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=self.project, check=True)
        (self.project / "README.md").write_text("base\n", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=self.project, check=True)
        subprocess.run(["git", "commit", "-qm", "base"], cwd=self.project, check=True)
        self.previous_db = os.environ.get("AXON_WATCH_CONTROL_PLANE_DB")
        os.environ["AXON_WATCH_CONTROL_PLANE_DB"] = str(base / "control.sqlite3")
        self.addCleanup(self._restore_env)

    def _restore_env(self) -> None:
        if self.previous_db is None:
            os.environ.pop("AXON_WATCH_CONTROL_PLANE_DB", None)
        else:
            os.environ["AXON_WATCH_CONTROL_PLANE_DB"] = self.previous_db

    def _patch_root(self):
        return patch.object(composer_sandbox, "resolve_workspace_root", return_value=self.project)

    def test_full_auto_is_lazy_and_concurrent_first_use_reuses_checkout(self) -> None:
        with self._patch_root(), patch.object(composer_sandbox, "_auto_enabled", return_value=True):
            status = composer_sandbox.sandbox_status("ws-auto")
            self.assertTrue(status["auto_enabled"])
            self.assertFalse(status["materialized"])
            with ThreadPoolExecutor(max_workers=4) as pool:
                roots = list(pool.map(lambda _: composer_sandbox.resolve_sandbox_workspace_root("ws-auto"), range(4)))
            self.assertEqual(len({str(root) for root in roots}), 1)
            self.assertTrue(composer_sandbox.sandbox_status("ws-auto")["materialized"])
            composer_sandbox.discard_sandbox("ws-auto")

    def test_manual_preference_survives_full_auto_exit(self) -> None:
        with self._patch_root(), patch.object(composer_sandbox, "_auto_enabled", return_value=False):
            composer_sandbox.enable_sandbox("ws-manual")
            composer_sandbox.reconcile_autonomy_transition("full", "semi")
            status = composer_sandbox.sandbox_status("ws-manual")
            self.assertTrue(status["manual_enabled"])
            self.assertTrue(status["materialized"])
            composer_sandbox.discard_sandbox("ws-manual")

    def test_auto_exit_retains_dirty_and_disable_conflicts(self) -> None:
        with self._patch_root(), patch.object(composer_sandbox, "_auto_enabled", return_value=True):
            root = composer_sandbox.resolve_sandbox_workspace_root("ws-dirty")
            assert root is not None
            (root / "README.md").write_text("changed\n", encoding="utf-8")
        composer_sandbox.reconcile_autonomy_transition("full", "semi")
        status = composer_sandbox.sandbox_status("ws-dirty")
        self.assertEqual(status["lifecycle"], "retained-dirty")
        self.assertFalse(status["can_disable"])
        with self.assertRaises(composer_sandbox.DirtySandboxError):
            composer_sandbox.disable_sandbox("ws-dirty")
        composer_sandbox.discard_sandbox("ws-dirty")

    def test_auto_exit_removes_clean_auto_only_checkout(self) -> None:
        with self._patch_root(), patch.object(composer_sandbox, "_auto_enabled", return_value=True):
            root = composer_sandbox.resolve_sandbox_workspace_root("ws-clean")
            assert root is not None
        composer_sandbox.reconcile_autonomy_transition("full", "semi")
        status = composer_sandbox.sandbox_status("ws-clean")
        self.assertFalse(status["materialized"])
        self.assertFalse(root.exists())

    def test_disable_clears_retained_marker_when_checkout_is_already_missing(self) -> None:
        composer_sandbox_store.save_state(
            "ws-missing", manual_enabled=True,
            checkout_id="missing", checkout_root=str(self.project / "missing"),
            retained_reason="Recovered unpromoted Sandbox changes",
        )
        with self._patch_root(), patch.object(composer_sandbox, "_auto_enabled", return_value=False):
            status = composer_sandbox.disable_sandbox("ws-missing")
        self.assertFalse(status["enabled"])
        self.assertEqual(status["retained_reason"], "")

    def test_effective_access_changes_only_tool_capable_modes(self) -> None:
        with self._patch_root(), patch.object(composer_sandbox, "_auto_enabled", return_value=True):
            root, ask_access = composer_sandbox.resolve_sandbox_execution("ws-access", "ask", "consultative")
            _, agent_access = composer_sandbox.resolve_sandbox_execution("ws-access", "agent", "consultative")
            self.assertEqual(ask_access, "consultative")
            self.assertEqual(agent_access, "full")
            self.assertIsNone(resolve_composer_execution_policy(root, "", "ask"))
            policy = resolve_composer_execution_policy(root, "", "agent")
            self.assertEqual(policy and policy.write_paths, (".",))
            composer_sandbox.discard_sandbox("ws-access")


if __name__ == "__main__":
    unittest.main()
