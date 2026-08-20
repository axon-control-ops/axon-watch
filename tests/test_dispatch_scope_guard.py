"""An implementation task must not be dispatched into a scope that cannot write it."""

from __future__ import annotations

import unittest
from dataclasses import dataclass
from unittest.mock import patch

from app.workspace_agents.worker_dispatch import _implementation_scope_block


@dataclass
class _Policy:
    write_paths: tuple[str, ...]
    execution_access: str = "full"


def _task(goal: str = "Implement the thing", **extra):
    return {"goal": goal, **extra}


class DispatchScopeGuardTests(unittest.TestCase):
    def test_expected_files_outside_write_scope_are_refused(self) -> None:
        # The real case: writes=command-centre,output/... but the task expects
        # docs/ops/school-running-plan.md. Unwinnable before the first token.
        with patch(
            "app.workspace_agents.completion_gate.implementation_requested", return_value=True
        ), patch(
            "app.workspace_agents.completion_gate.expected_files_for_task",
            return_value=["docs/ops/school-running-plan.md"],
        ):
            reason = _implementation_scope_block(
                task=_task(),
                execution_policy=_Policy(("command-centre", "output/homework")),
            )
        self.assertIsNotNone(reason)
        self.assertIn("docs/ops/school-running-plan.md", reason)
        self.assertIn("command-centre", reason)

    def test_empty_write_scope_is_refused(self) -> None:
        with patch(
            "app.workspace_agents.completion_gate.implementation_requested", return_value=True
        ), patch(
            "app.workspace_agents.completion_gate.expected_files_for_task", return_value=[]
        ):
            reason = _implementation_scope_block(
                task=_task(), execution_policy=_Policy((), execution_access="consultative")
            )
        self.assertIsNotNone(reason)
        self.assertIn("no writable scope", reason)

    def test_covered_expectation_is_allowed(self) -> None:
        with patch(
            "app.workspace_agents.completion_gate.implementation_requested", return_value=True
        ), patch(
            "app.workspace_agents.completion_gate.expected_files_for_task",
            return_value=["website/index.html"],
        ):
            self.assertIsNone(
                _implementation_scope_block(
                    task=_task(), execution_policy=_Policy(("website",))
                )
            )

    def test_partial_overlap_still_runs(self) -> None:
        # One writable target is enough; do not block on the others.
        with patch(
            "app.workspace_agents.completion_gate.implementation_requested", return_value=True
        ), patch(
            "app.workspace_agents.completion_gate.expected_files_for_task",
            return_value=["docs/ops/plan.md", "website/index.html"],
        ):
            self.assertIsNone(
                _implementation_scope_block(
                    task=_task(), execution_policy=_Policy(("website",))
                )
            )

    def test_non_implementation_tasks_are_untouched(self) -> None:
        # Analysis / review / receipt-backed ops runs legitimately write nothing.
        with patch(
            "app.workspace_agents.completion_gate.implementation_requested", return_value=False
        ):
            self.assertIsNone(
                _implementation_scope_block(task=_task(), execution_policy=_Policy(()))
            )


if __name__ == "__main__":
    unittest.main()
