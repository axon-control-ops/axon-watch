"""Auto-created tasks record useful path hints without defining authority.

The effective execution policy now gets write authority from the employee's
role, explicit employee override, and repository contract. ``allowed_paths``
on a task remains useful routing/acceptance metadata but cannot accidentally
strand a colleague in a read-only sandbox.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.persistence import run_store, task_store  # noqa: E402
from app.workspace_agents.execution_policy import (  # noqa: E402
    resolve_effective_policy,
    role_execution_policy,
)


class TaskDefaultRoleScopeTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)
        task_store.reset_store()
        self.addCleanup(task_store.reset_store)

    def _create(self, **kwargs) -> dict:
        payload = {"workspace_id": "workspace_axon_watch", "goal": "do the thing"}
        payload.update(kwargs)
        return task_store.create_task(**payload)

    def test_unscoped_backend_task_inherits_the_backend_write_boundary(self) -> None:
        task = self._create(owner_role="backend")
        expected = list(role_execution_policy("backend").write_paths)
        self.assertTrue(expected, "precondition: backend role should have write paths")
        self.assertEqual(expected, task["allowed_paths"])

    def test_watcher_task_inherits_its_operational_role_lane(self) -> None:
        self.assertTrue(role_execution_policy("watcher").write_paths)
        task = self._create(owner_role="watcher")
        self.assertEqual(
            list(role_execution_policy("watcher").write_paths),
            task["allowed_paths"],
        )

    def test_explicit_scope_is_never_overridden(self) -> None:
        task = self._create(owner_role="backend", allowed_paths=["services/control-plane/"])
        self.assertEqual(["services/control-plane/"], task["allowed_paths"])

    def test_explicit_scope_may_be_narrower_than_the_role_default(self) -> None:
        role_paths = set(role_execution_policy("backend").write_paths)
        task = self._create(owner_role="backend", allowed_paths=["services/"])
        self.assertEqual(["services/"], task["allowed_paths"])
        self.assertNotEqual(role_paths, set(task["allowed_paths"]))

    def test_task_without_owner_role_gets_no_scope(self) -> None:
        task = self._create(owner_role="")
        self.assertEqual([], task["allowed_paths"])

    def test_unknown_role_does_not_crash_and_stays_conservative(self) -> None:
        task = self._create(owner_role="not_a_real_role")
        fallback = list(role_execution_policy("not_a_real_role").write_paths)
        self.assertEqual(fallback, task["allowed_paths"])


class EffectivePolicyEndToEndTests(unittest.TestCase):
    """The scope only matters if it survives into the resolved execution policy."""

    # Verbatim allowed_paths from the real axon-watch project contract, which
    # does load (verified against live isolation worktrees). Passing () here
    # instead would wipe write_paths on its own — resolve_effective_policy
    # intersects with the workspace scope too — and would test nothing.
    WORKSPACE_SCOPE = (
        "app/",
        "apps/",
        "components/",
        "features/",
        "hooks/",
        "locales/",
        "services/",
        "packages/",
        "scripts/",
        "tests/",
        "config/",
        "docs/",
        ".github/",
    )

    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)
        task_store.reset_store()
        self.addCleanup(task_store.reset_store)

    def _policy_for(self, owner_role: str, allowed_paths=None):
        task = task_store.create_task(
            workspace_id="workspace_axon_watch",
            goal="fix the thing",
            owner_role=owner_role,
            allowed_paths=allowed_paths,
        )
        return task, resolve_effective_policy(
            role=owner_role,
            employee_override=None,
            workspace_allowed_paths=self.WORKSPACE_SCOPE,
            workspace_forbidden_path_globs=(),
            task_allowed_paths=task["allowed_paths"],
        )

    def test_backend_fix_task_can_actually_write(self) -> None:
        # This is the regression: before the fix this resolved to
        # write_paths=() and execution_access="consultative", so an agent asked
        # to fix something could not modify a file.
        _task, policy = self._policy_for("backend")
        self.assertTrue(policy.write_paths, "backend fix task must be able to write")
        self.assertNotEqual("consultative", policy.execution_access)

    def test_frontend_fix_task_can_edit_hooks(self) -> None:
        _task, policy = self._policy_for("frontend")
        self.assertIn("hooks", policy.write_paths)
        self.assertNotEqual("consultative", policy.execution_access)

    def test_legacy_frontend_ui_scope_self_heals_hooks(self) -> None:
        _task, policy = self._policy_for(
            "frontend",
            allowed_paths=["app", "components", "tests", "locales"],
        )
        self.assertIn("hooks", policy.write_paths)

    def test_watcher_task_has_its_contract_bounded_operational_lane(self) -> None:
        _task, policy = self._policy_for("watcher")
        self.assertEqual(("docs/ops", "scripts/guardrails"), policy.write_paths)
        self.assertEqual("full", policy.execution_access)

    def test_explicit_task_scope_is_a_hint_not_an_authority_reduction(self) -> None:
        _task, policy = self._policy_for("backend", allowed_paths=["services/"])
        self.assertIn("services", policy.write_paths)
        self.assertIn("tests", policy.write_paths)

    def test_role_ceiling_still_bounds_an_overbroad_task_scope(self) -> None:
        # A task asking for the repo root must not escape the role boundary.
        # The effective ceiling includes non-standard role paths explicitly
        # declared by this workspace contract (for backend, docs/ops).
        _task, policy = self._policy_for("backend", allowed_paths=["."])
        expected = resolve_effective_policy(
            role="backend",
            employee_override=None,
            workspace_allowed_paths=self.WORKSPACE_SCOPE,
            workspace_forbidden_path_globs=(),
            task_allowed_paths=None,
        )
        self.assertEqual(expected.write_paths, policy.write_paths)


if __name__ == "__main__":
    unittest.main()
