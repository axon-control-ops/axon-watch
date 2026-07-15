"""Safe-improvement vertical-slice contract tests."""

from __future__ import annotations

import os
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from app.safe_improvement import isolated_executor, proposal_service, store
from app.safe_improvement.policy import effect_fingerprint
from app.safe_improvement.verifier import evaluate_against_threshold
from app.safe_improvement.models import EvaluationCase


class SafeImprovementTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self._db = Path(self._tmpdir.name) / "si.sqlite3"
        os.environ["AXON_WATCH_CONTROL_PLANE_DB"] = str(self._db)

    def tearDown(self) -> None:
        self._tmpdir.cleanup()
        os.environ.pop("AXON_WATCH_CONTROL_PLANE_DB", None)

    def _awaiting_proposal(self, effect_kind: str = "merge"):
        trace = proposal_service.capture_trace(
            workspace_id="ws_demo",
            source_kind="run",
            source_ref="run_gate",
            summary="gate test",
        )
        case = proposal_service.upsert_evaluation_case(
            name="gate metric",
            metric="latency_ms",
            threshold=10.0,
            comparator="lte",
            baseline_value=100.0,
        )
        proposal = proposal_service.create_proposal(
            workspace_id="ws_demo",
            trace_id=trace.trace_id,
            case_id=case.case_id,
            title="bounded candidate",
            effect_kind=effect_kind,
            target_ref="main",
        )
        proposal_service.evaluate_proposal(proposal.proposal_id, candidate_value=95.0)
        return proposal_service.request_exact_approval(
            proposal.proposal_id,
            target_ref="main",
        )

    def test_threshold_blocks_regression(self) -> None:
        case = EvaluationCase(
            case_id="c1",
            name="latency",
            metric="latency_ms",
            threshold=5.0,
            comparator="lte",
        )
        result = evaluate_against_threshold(
            case,
            baseline_value=100.0,
            candidate_value=120.0,
        )
        self.assertFalse(result.passed)

    def test_isolation_does_not_touch_bound_root(self) -> None:
        bound = Path(self._tmpdir.name) / "bound-workspace"
        bound.mkdir()
        sentinel = bound / "IMPORTANT.txt"
        sentinel.write_text("keep\n", encoding="utf-8")
        root = isolated_executor.create_isolation_root(proposal_id="prop_test")
        isolated_executor.apply_candidate_change(
            root,
            metric="latency_ms",
            candidate_value=90.0,
        )
        self.assertTrue(sentinel.exists())
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep\n")
        self.assertNotEqual(root.resolve(), bound.resolve())

    def test_happy_path_merge_with_exact_approval_and_rollback(self) -> None:
        trace = proposal_service.capture_trace(
            workspace_id="ws_demo",
            source_kind="run",
            source_ref="run_abc",
            summary="baseline latency turn",
            receipt_refs=["rcpt_1"],
        )
        case = proposal_service.upsert_evaluation_case(
            name="latency gate",
            metric="latency_ms",
            threshold=10.0,
            comparator="lte",
            baseline_value=100.0,
        )
        proposal = proposal_service.create_proposal(
            workspace_id="ws_demo",
            trace_id=trace.trace_id,
            case_id=case.case_id,
            title="trim voice prefetch",
            effect_kind="merge",
            target_ref="main",
        )
        evaluated = proposal_service.evaluate_proposal(
            proposal.proposal_id,
            candidate_value=95.0,
        )
        self.assertEqual(evaluated.status, "evaluated")
        self.assertTrue(evaluated.verification and evaluated.verification.passed)

        awaiting = proposal_service.request_exact_approval(
            proposal.proposal_id,
            target_ref="main",
        )
        self.assertEqual(awaiting.status, "awaiting_approval")
        assert awaiting.approval is not None

        with self.assertRaises(ValueError):
            proposal_service.approve_exact_effect(
                proposal.proposal_id,
                effect_fingerprint="eff_wrong",
            )

        approved = proposal_service.approve_exact_effect(
            proposal.proposal_id,
            effect_fingerprint=awaiting.approval.effect_fingerprint,
        )
        self.assertEqual(approved.status, "approved")

        executed = proposal_service.execute_approved_proposal(proposal.proposal_id)
        self.assertEqual(executed.status, "verified")
        promoted = Path(executed.isolation_root or "") / "PROMOTED"
        self.assertTrue(promoted.exists())

        rolled = proposal_service.rollback_proposal(proposal.proposal_id)
        self.assertEqual(rolled.status, "rolled_back")
        self.assertEqual(rolled.candidate_marker, "baseline")
        self.assertFalse(promoted.exists())

    def test_fingerprint_changes_when_target_changes(self) -> None:
        left = effect_fingerprint(
            proposal_id="prop_1",
            effect_kind="merge",
            target_ref="main",
            payload={"title": "x"},
        )
        right = effect_fingerprint(
            proposal_id="prop_1",
            effect_kind="merge",
            target_ref="dev",
            payload={"title": "x"},
        )
        self.assertNotEqual(left, right)

    def test_expired_exact_effect_approval_is_rejected(self) -> None:
        awaiting = self._awaiting_proposal()
        assert awaiting.approval is not None
        awaiting.approval = replace(awaiting.approval, expires_at="2000-01-01T00:00:00Z")
        store.save_proposal(awaiting)

        with self.assertRaisesRegex(ValueError, "approval expired"):
            proposal_service.approve_exact_effect(
                awaiting.proposal_id,
                effect_fingerprint=awaiting.approval.effect_fingerprint,
            )

    def test_reserved_effect_cannot_execute(self) -> None:
        awaiting = self._awaiting_proposal(effect_kind="policy")
        assert awaiting.approval is not None
        approved = proposal_service.approve_exact_effect(
            awaiting.proposal_id,
            effect_fingerprint=awaiting.approval.effect_fingerprint,
        )

        with self.assertRaisesRegex(ValueError, "effect `policy` is reserved"):
            proposal_service.execute_approved_proposal(approved.proposal_id)


if __name__ == "__main__":
    unittest.main()
