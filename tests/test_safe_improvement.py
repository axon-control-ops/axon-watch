"""Safe-improvement vertical-slice contract tests."""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from app.safe_improvement import isolated_executor, proposal_service, store
from app.safe_improvement.policy import effect_fingerprint
from app.safe_improvement.verifier import evaluate_against_threshold
from app.safe_improvement.models import EvaluationCase


def _init_git_repo(path: Path) -> str:
    path.mkdir(parents=True, exist_ok=True)
    (path / "README.md").write_text("bound project\n", encoding="utf-8")
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "si-test@example.com"],
        cwd=path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "SI Test"],
        cwd=path,
        check=True,
        capture_output=True,
    )
    subprocess.run(["git", "add", "README.md"], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "baseline"],
        cwd=path,
        check=True,
        capture_output=True,
    )
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return commit


class SafeImprovementTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self._db = Path(self._tmpdir.name) / "si.sqlite3"
        os.environ["AXON_WATCH_CONTROL_PLANE_DB"] = str(self._db)
        self._bound = Path(self._tmpdir.name) / "bound-workspace"
        self._bound_commit = _init_git_repo(self._bound)
        (self._bound / "IMPORTANT.txt").write_text("keep\n", encoding="utf-8")

    def tearDown(self) -> None:
        for proposal in store.list_proposals(limit=100):
            root = proposal.get("isolation_root")
            if root and Path(str(root)).exists():
                isolated_executor.cleanup_isolation_root(Path(str(root)))
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
        proposal_service.evaluate_proposal(
            proposal.proposal_id,
            candidate_value=95.0,
            bound_project_root=self._bound,
        )
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
        sentinel = self._bound / "IMPORTANT.txt"
        before = sentinel.read_text(encoding="utf-8")
        dirty = self._bound / "DIRTY_LOCAL.txt"
        dirty.write_text("uncommitted\n", encoding="utf-8")

        root = isolated_executor.create_isolation_root(
            proposal_id="prop_test",
            bound_project_root=self._bound,
        )
        isolated_executor.apply_candidate_change(
            root,
            metric="latency_ms",
            candidate_value=90.0,
        )
        meta = isolated_executor.read_baseline_metadata(root)
        agent_root = isolated_executor.agent_workspace_for_isolation(root)

        self.assertTrue(sentinel.exists())
        self.assertEqual(sentinel.read_text(encoding="utf-8"), before)
        self.assertEqual(dirty.read_text(encoding="utf-8"), "uncommitted\n")
        self.assertNotEqual(root.resolve(), self._bound.resolve())
        self.assertEqual(meta["baseline_commit"], self._bound_commit)
        self.assertIn(meta["isolation_kind"], {"worktree", "shallow_clone"})
        self.assertEqual(agent_root, root.resolve())
        self.assertTrue((root / ".axon-si" / "MARKER").is_file())

        cleanup = isolated_executor.cleanup_isolation_root(root)
        self.assertTrue(cleanup["cleaned"] or cleanup["removed"])
        self.assertFalse(root.exists())
        self.assertEqual(sentinel.read_text(encoding="utf-8"), before)
        self.assertTrue(dirty.exists())

    def test_agent_workspace_rejects_missing_isolation(self) -> None:
        with self.assertRaises(isolated_executor.IsolationError):
            isolated_executor.agent_workspace_for_isolation(None)

    def test_creation_fails_closed_for_non_git_bound_root(self) -> None:
        plain = Path(self._tmpdir.name) / "not-a-repo"
        plain.mkdir()
        with self.assertRaises(isolated_executor.IsolationError):
            isolated_executor.create_isolation_root(
                proposal_id="prop_fail",
                bound_project_root=plain,
            )
        self.assertEqual(list(plain.iterdir()), [])

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
            bound_project_root=self._bound,
        )
        self.assertEqual(evaluated.status, "evaluated")
        self.assertTrue(evaluated.verification and evaluated.verification.passed)
        self.assertEqual(evaluated.baseline_commit, self._bound_commit)
        isolation_root = Path(evaluated.isolation_root or "")
        self.assertTrue(isolation_root.is_dir())
        self.assertEqual(
            proposal_service.sandbox_agent_workspace(proposal.proposal_id),
            isolation_root.resolve(),
        )

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
        promoted = Path(executed.isolation_root or "") / ".axon-si" / "PROMOTED"
        self.assertTrue(promoted.exists())

        rolled = proposal_service.rollback_proposal(proposal.proposal_id)
        self.assertEqual(rolled.status, "rolled_back")
        self.assertEqual(rolled.candidate_marker, "baseline")
        self.assertFalse(isolation_root.exists())
        self.assertEqual(
            (self._bound / "IMPORTANT.txt").read_text(encoding="utf-8"),
            "keep\n",
        )
        cleanup_kinds = {r.get("kind") for r in rolled.receipts}
        self.assertIn("rollback", cleanup_kinds)
        self.assertIn("isolation_cleanup", cleanup_kinds)

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
