"""Independent review + draft PR / CI remediation loop tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.workspace_agents.review_pr_loop import (  # noqa: E402
    RepairLoopState,
    build_draft_pr_plan,
    diagnose_ci_failure,
    remediation_loop_step,
    review_task_diff,
    should_publish_draft_pr,
)


class ReviewPrLoopTests(unittest.TestCase):
    def test_independent_review_blocks_on_missing_verifier(self) -> None:
        verdict = review_task_diff(
            implementer="implementer",
            reviewer="reviewer",
            task_contract={"acceptance_criteria": "tests pass"},
            diff_summary="touch apps/x.ts",
            verifier_receipts=[],
        )
        self.assertFalse(verdict.passed)
        self.assertTrue(verdict.blocking)

    def test_same_actor_cannot_self_review(self) -> None:
        with self.assertRaises(ValueError):
            review_task_diff(
                implementer="mira",
                reviewer="mira",
                task_contract={"acceptance_criteria": "ok"},
                diff_summary="",
                verifier_receipts=[{"passed": True}],
            )

    def test_publish_requires_review_and_verifier(self) -> None:
        verdict = review_task_diff(
            implementer="implementer",
            reviewer="reviewer",
            task_contract={"acceptance_criteria": "ok"},
            diff_summary="clean change",
            verifier_receipts=[{"passed": True}],
        )
        self.assertTrue(verdict.passed)
        self.assertTrue(should_publish_draft_pr(verdict, True))
        self.assertFalse(should_publish_draft_pr(verdict, False))

    def test_ci_remediation_repairs_seeded_failure_without_new_prompt(self) -> None:
        state = RepairLoopState(max_attempts=3)
        seed = "FAIL shell.ts: critical hotspot changed without shrinking below ratchet"
        step = remediation_loop_step(
            state,
            log_excerpt=seed,
            elapsed_delta_seconds=30,
            tokens_delta=1200,
        )
        self.assertTrue(step["continue"])
        self.assertEqual("file_size_ratchet", step["diagnosis"]["category"])
        plan = build_draft_pr_plan(
            workspace_id="workspace_axon_watch",
            task_id="task_seed_ci",
            goal="repair seeded Fast Gate hotspot failure",
            evidence_links=["receipt://acceptance"],
            ci_failure_seed=seed,
        )
        self.assertTrue(plan.draft)
        self.assertIn("Seeded CI failure", plan.body)

    def test_repair_loop_stops_at_budget(self) -> None:
        state = RepairLoopState(max_attempts=1)
        first = remediation_loop_step(
            state,
            log_excerpt="vitest failed",
            elapsed_delta_seconds=10,
            tokens_delta=10,
        )
        self.assertTrue(first["continue"])
        self.assertFalse(first["more_attempts_allowed"])
        second = remediation_loop_step(
            state,
            log_excerpt="vitest failed again",
            elapsed_delta_seconds=10,
            tokens_delta=10,
        )
        self.assertFalse(second["continue"])
        self.assertIn("budget", second["reason"])


if __name__ == "__main__":
    unittest.main()
