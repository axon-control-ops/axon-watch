"""Retry/review shifts must be handed the artifacts they are asked to review."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.workspace_agents.prior_shift_evidence import (  # noqa: E402
    looks_like_review_or_retry,
    prior_shift_evidence_clause,
)

MODULE = "app.workspace_agents.prior_shift_evidence"


class ReviewIntentTests(unittest.TestCase):
    def test_detects_review_and_retry_phrasing(self) -> None:
        for text in (
            "Critically review all your previous work for factual errors",
            "Retry the failed backend shift",
            "Re-check your last shift and rewrite the answer",
            "Revisit prior work on the lessons service",
        ):
            with self.subTest(text=text):
                self.assertTrue(looks_like_review_or_retry(text))

    def test_ignores_ordinary_implementation_goals(self) -> None:
        for text in ("Add a lessons service unit test", "Fix the teacher dashboard layout"):
            with self.subTest(text=text):
                self.assertFalse(looks_like_review_or_retry(text))


class PriorShiftEvidenceTests(unittest.TestCase):
    def _clause(self, *, outcome, delivery=None, history=None) -> str:
        with patch(
            "app.workspace_agents.run_outcome.latest_role_run_outcome",
            return_value=outcome,
        ), patch(
            "app.workspace_delivery.store.get_delivery_by_run",
            return_value=delivery,
        ), patch(
            "app.persistence.run_store.get_run",
            return_value={"history_ref": "hist-1"},
        ), patch(
            "app.persistence.run_store.list_history",
            return_value=history or [],
        ):
            return prior_shift_evidence_clause(
                workspace_id="workspace_dashpro",
                role="backend",
            )

    def test_names_pr_branch_commit_and_changed_files(self) -> None:
        clause = self._clause(
            outcome={"run_id": "run_abc123", "outcome": "failed", "detail": "gate blocked"},
            delivery={
                "worker_branch": "worker/run_abc123",
                "commit_sha": "0123456789abcdef",
                "draft_pr_url": "https://github.com/acme/app/pull/96",
            },
            history=[
                {
                    "receipt": {
                        "type": "completion_gate",
                        "summary": (
                            "completion=fail · reason=implementation requested but worker "
                            "produced no changed files · changed_files=services/api.ts, "
                            "lib/db.ts · validation=not checked"
                        ),
                    }
                }
            ],
        )
        self.assertIn("run_abc123", clause)
        self.assertIn("https://github.com/acme/app/pull/96", clause)
        self.assertIn("worker/run_abc123", clause)
        self.assertIn("0123456789ab", clause)
        self.assertIn("services/api.ts", clause)
        self.assertIn("implementation requested but worker produced no changed files", clause)

    def test_says_plainly_when_there_is_nothing_to_review(self) -> None:
        clause = self._clause(outcome={"run_id": "run_empty", "outcome": "failed", "detail": ""})
        self.assertIn("no delivery branch, commit, PR, or changed files", clause)
        self.assertIn("ask for a pointer", clause)
        self.assertNotIn("draft PR", clause)

    def test_no_prior_run_yields_no_clause(self) -> None:
        self.assertEqual("", self._clause(outcome=None))
        self.assertEqual("", self._clause(outcome={"run_id": "", "outcome": "failed"}))

    def test_lookup_failure_does_not_break_dispatch(self) -> None:
        with patch(
            "app.workspace_agents.run_outcome.latest_role_run_outcome",
            return_value={"run_id": "run_x", "outcome": "failed", "detail": "boom"},
        ), patch(
            "app.workspace_delivery.store.get_delivery_by_run",
            side_effect=RuntimeError("db down"),
        ), patch(
            "app.persistence.run_store.get_run",
            side_effect=RuntimeError("db down"),
        ):
            clause = prior_shift_evidence_clause(
                workspace_id="workspace_dashpro",
                role="backend",
            )
        self.assertIn("run_x", clause)
        self.assertIn("boom", clause)


class PriorShiftEvidencePromptWiringTests(unittest.TestCase):
    def _prompt(self, goal: str) -> str:
        from app.workspace_agents.config_loader import EmployeeConfig
        from app.workspace_agents.worker_prompt import build_continuous_worker_prompt

        # worker_prompt imports the symbol directly, so patch it in that namespace.
        with patch(
            "app.workspace_agents.worker_prompt.prior_shift_evidence_clause",
            return_value=" PRIOR SHIFT EVIDENCE: prior run `run_probe`.",
        ):
            return build_continuous_worker_prompt(
                workspace_id="workspace_probe",
                employee=EmployeeConfig(name="Probe", role="backend", owns="probe"),
                task={"task_id": "task-probe", "goal": goal},
            )

    def test_review_goal_receives_prior_artifacts(self) -> None:
        prompt = self._prompt("Critically review all your previous work and rewrite it")
        self.assertIn("PRIOR SHIFT EVIDENCE", prompt)

    def test_plain_implementation_goal_does_not(self) -> None:
        prompt = self._prompt("Add a lessons service unit test")
        self.assertNotIn("PRIOR SHIFT EVIDENCE", prompt)


if __name__ == "__main__":
    unittest.main()
