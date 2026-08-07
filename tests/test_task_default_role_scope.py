"""Auto-created tasks must carry a write scope, or they cannot do their job.

A task with no allowed_paths is fail-closed downstream by design: the
effective execution policy intersects the role's write_paths with the task
scope, and execution_policy.py::_intersect_path_scopes returns () when either
side is empty. Empty write_paths then downgrades the run to
consultative/read-only, and the bwrap sandbox mounts nothing writable.

That rule is deliberate ("Resolve role, employee, contract, and leased-task
scope fail closed" — execution_policy_runtime.py) and is NOT changed here.

The defect was that nearly every auto-created task omitted allowed_paths:
CI repair, VAXON attend, VAXON fleet repair, Lead fan-out. Tasks whose entire
purpose is to FIX something were structurally unable to write a single byte.
Measured on the live host: 52 of 52 agent_execution_policy receipts in a 24h
window read `writes=read-only`, and 27 of 27 preserved isolation worktrees
contained zero agent-authored files.

create_task now resolves an unset scope to the owning role's own documented
write boundary. That is bounded, not permissive — the role ceiling is
unchanged, and roles that are read-only by design stay read-only.
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

    def test_read_only_role_stays_read_only(self) -> None:
        # watcher's role write_paths are () by design — it is a health/triage
        # role. Defaulting must not invent write access for it.
        self.assertEqual((), role_execution_policy("watcher").write_paths)
        task = self._create(owner_role="watcher")
        self.assertEqual([], task["allowed_paths"])

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
        "apps/", "services/", "packages/", "scripts/", "tests/", "config/", "docs/", ".github/",
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

    def test_watcher_task_remains_consultative(self) -> None:
        _task, policy = self._policy_for("watcher")
        self.assertEqual((), policy.write_paths)
        self.assertEqual("consultative", policy.execution_access)

    def test_explicit_narrow_scope_still_narrows_the_policy(self) -> None:
        _task, policy = self._policy_for("backend", allowed_paths=["services/"])
        self.assertTrue(policy.write_paths)
        for path in policy.write_paths:
            self.assertTrue(
                str(path).startswith("services"),
                f"explicit scope must bound the policy, got {path}",
            )

    def test_role_ceiling_still_bounds_an_overbroad_task_scope(self) -> None:
        # A task asking for the repo root must not escape the role boundary —
        # the intersection with role write_paths is what enforces that.
        _task, policy = self._policy_for("backend", allowed_paths=["."])
        role_paths = set(role_execution_policy("backend").write_paths)
        for path in policy.write_paths:
            self.assertIn(
                str(path),
                role_paths,
                "task scope must not widen beyond the role ceiling",
            )


if __name__ == "__main__":
    unittest.main()
