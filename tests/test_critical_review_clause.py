"""Unit tests for the mandatory Critical Review Clause helpers and finalize gate."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.chat.lane_b_plan_run import finalize_lane_b_plan_run  # noqa: E402
from app.chat.lane_b_stream_execute import finalize_lane_b_agent_run  # noqa: E402
from app.persistence import run_store  # noqa: E402
from app.runs.service import create_run  # noqa: E402
from app.workspace_agents.critical_review_clause import (  # noqa: E402
    CRITICAL_REVIEW_CLAUSE,
    append_critical_review_clause,
    parse_confidence,
    resolve_critical_review_confidence,
)
from app.workspace_agents.config_loader import EmployeeConfig  # noqa: E402
from app.workspace_agents.worker_prompt import build_continuous_worker_prompt  # noqa: E402
from tests.support.control_plane_db import isolate_control_plane_db  # noqa: E402


class CriticalReviewClauseHelperTests(unittest.TestCase):
    def test_append_is_idempotent_and_includes_canonical_text(self) -> None:
        once = append_critical_review_clause("Do the work.")
        self.assertIn(CRITICAL_REVIEW_CLAUSE, once)
        self.assertIn("Confidence: X/10", once)
        twice = append_critical_review_clause(once)
        self.assertEqual(once, twice)

    def test_parse_confidence_reads_last_valid_score(self) -> None:
        self.assertEqual(parse_confidence("Confidence: 7/10"), 7)
        self.assertEqual(parse_confidence("Draft.\nConfidence: 3/10\nRewrite.\nConfidence: 9/10"), 9)
        self.assertEqual(parse_confidence("Done.\nConfidence 8/10"), 8)
        self.assertIsNone(parse_confidence("no score here"))
        self.assertIsNone(parse_confidence("Confidence: 0/10"))
        self.assertIsNone(parse_confidence("Confidence: 11/10"))

    def test_resolve_auto_recovers_substantive_reply_without_score(self) -> None:
        long_reply = (
            "Verified control plane health and production site HTTP 200. "
            "Traced red CI on main to a missing contract coverage gap and added "
            "local contract checks that pass. Remote CI stays red until the fix "
            "is committed and pushed on operator go-ahead. Next Soren confirms "
            "green main reaches Vercel after the push lands."
        )
        confidence, recovered = resolve_critical_review_confidence(long_reply)
        self.assertEqual(6, confidence)
        self.assertTrue(recovered)
        short = resolve_critical_review_confidence("Finished the edit without a score.")
        self.assertEqual((None, False), short)


class CriticalReviewPromptContractTests(unittest.TestCase):
    def test_every_continuous_role_includes_exact_clause(self) -> None:
        for role in ("frontend", "backend", "integrations", "watcher"):
            with self.subTest(role=role):
                prompt = build_continuous_worker_prompt(
                    workspace_id="workspace_axon_watch",
                    employee=EmployeeConfig(
                        name=f"Teammate {role}",
                        role=role,
                        owns="in-scope work",
                        schedule="continuous",
                    ),
                )
                self.assertIn(CRITICAL_REVIEW_CLAUSE, prompt)
                self.assertIn("Confidence: X/10", prompt)


class CriticalReviewFinalizeGateTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)

    def test_agent_finalize_fails_closed_without_confidence(self) -> None:
        created = create_run(
            workspace_id="workspace_alpha",
            summary="agent shift",
            mode="agent",
        )
        run_id = str(created["run_id"])
        dispatched, record = finalize_lane_b_agent_run(
            dispatch_run_id=run_id,
            lane_b_result={"dispatched": True, "runtime_label": "Cursor CLI"},
            reply_text="Finished the edit without a score.",
        )
        self.assertFalse(dispatched)
        assert record is not None
        self.assertEqual("failed", record["phase"])
        self.assertIn(
            "Confidence: N/10",
            str(record.get("current_step") or record.get("detail") or ""),
        )

    def test_agent_finalize_auto_recovers_substantive_reply_without_score(self) -> None:
        created = create_run(
            workspace_id="workspace_alpha",
            summary="agent shift",
            mode="agent",
        )
        run_id = str(created["run_id"])
        long_reply = (
            "Verified control plane health and production site HTTP 200. "
            "Traced red CI on main to a missing contract coverage gap and added "
            "local contract checks that pass. Remote CI stays red until the fix "
            "is committed and pushed on operator go-ahead. Next Soren confirms "
            "green main reaches Vercel after the push lands."
        )
        dispatched, record = finalize_lane_b_agent_run(
            dispatch_run_id=run_id,
            lane_b_result={"dispatched": True, "runtime_label": "Cursor CLI"},
            reply_text=long_reply,
        )
        self.assertTrue(dispatched)
        assert record is not None
        self.assertEqual("completed", record["phase"])

    def test_agent_finalize_completes_with_confidence_receipt(self) -> None:
        created = create_run(
            workspace_id="workspace_alpha",
            summary="agent shift",
            mode="agent",
        )
        run_id = str(created["run_id"])
        dispatched, record = finalize_lane_b_agent_run(
            dispatch_run_id=run_id,
            lane_b_result={"dispatched": True, "runtime_label": "Cursor CLI"},
            reply_text="Done.\n\nConfidence: 8/10",
        )
        self.assertTrue(dispatched)
        assert record is not None
        self.assertEqual("completed", record["phase"])

    def test_plan_finalize_fails_closed_without_confidence(self) -> None:
        created = create_run(
            workspace_id="workspace_alpha",
            summary="plan shift",
            mode="plan",
        )
        run_id = str(created["run_id"])
        dispatched, record = finalize_lane_b_plan_run(
            run_id=run_id,
            lane_b_result={"dispatched": True, "runtime_label": "Cursor CLI"},
            reply_text="# Plan\n\nNo confidence line.",
        )
        self.assertFalse(dispatched)
        assert record is not None
        self.assertEqual("failed", record["phase"])


if __name__ == "__main__":
    unittest.main()
