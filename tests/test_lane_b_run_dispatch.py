"""Tests for Lane B agent run resolution (G3.8)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.chat.lane_b_run_dispatch import resolve_lane_b_agent_run  # noqa: E402
from app.chat.lane_b_plan_run import finalize_lane_b_plan_run  # noqa: E402
from app.persistence import run_store  # noqa: E402
from app.runs.service import approve_run, create_run, stop_run  # noqa: E402
from tests.support.control_plane_db import isolate_control_plane_db  # noqa: E402


class LaneBRunDispatchTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)

    def test_full_access_run_executes_immediately_without_approval(self) -> None:
        # Consent in the Agent Dock is the approval; no run-level boundary.
        record = resolve_lane_b_agent_run(
            workspace_id="workspace_alpha",
            content="Implement the toggle",
            linked_run_id=None,
            execution_access="full",
        )
        self.assertEqual("executing", record["phase"])
        self.assertFalse(record["can_approve"])

    def test_consultative_agent_run_enters_executing_without_approval(self) -> None:
        record = resolve_lane_b_agent_run(
            workspace_id="workspace_alpha",
            content="Suggest next steps",
            linked_run_id=None,
            execution_access="consultative",
        )
        self.assertEqual("executing", record["phase"])

    def test_plan_run_is_linked_and_becomes_review_ready(self) -> None:
        created = resolve_lane_b_agent_run(
            workspace_id="workspace_alpha",
            content="Plan the resume behavior",
            linked_run_id=None,
            execution_access="consultative",
            composer_mode="plan",
        )
        self.assertEqual("plan", created["mode"])
        self.assertEqual("executing", created["phase"])
        self.assertFalse(created["can_approve"])

        dispatched, reviewed = finalize_lane_b_plan_run(
            run_id=str(created["run_id"]),
            lane_b_result={
                "dispatched": True,
                "runtime_label": "Cursor CLI",
            },
        )
        self.assertTrue(dispatched)
        self.assertIsNotNone(reviewed)
        self.assertEqual("review_ready", reviewed["phase"])

        resumed = resolve_lane_b_agent_run(
            workspace_id="workspace_alpha",
            content="Revise the verification step",
            linked_run_id=str(created["run_id"]),
            execution_access="consultative",
            composer_mode="plan",
        )
        self.assertEqual(str(created["run_id"]), str(resumed["run_id"]))
        self.assertEqual("executing", resumed["phase"])

    def test_reuses_executing_run_for_follow_up_turn(self) -> None:
        created = resolve_lane_b_agent_run(
            workspace_id="workspace_alpha",
            content="First turn",
            linked_run_id=None,
            execution_access="full",
        )
        self.assertEqual("executing", created["phase"])

        reused = resolve_lane_b_agent_run(
            workspace_id="workspace_alpha",
            content="Second turn",
            linked_run_id=str(created["run_id"]),
            execution_access="full",
        )
        self.assertEqual(str(created["run_id"]), str(reused["run_id"]))

    def test_full_access_auto_approves_legacy_awaiting_approval_run(self) -> None:
        legacy = create_run(
            workspace_id="workspace_alpha",
            mode="agent",
            summary="Legacy boundary run",
            requires_approval=True,
        )
        self.assertEqual("awaiting_approval", legacy["phase"])

        resolved = resolve_lane_b_agent_run(
            workspace_id="workspace_alpha",
            content="Follow-up",
            linked_run_id=str(legacy["run_id"]),
            execution_access="full",
        )
        self.assertEqual(str(legacy["run_id"]), str(resolved["run_id"]))
        self.assertEqual("executing", resolved["phase"])

    def test_full_access_resumes_review_ready_linked_run(self) -> None:
        created = resolve_lane_b_agent_run(
            workspace_id="workspace_alpha",
            content="First turn",
            linked_run_id=None,
            execution_access="full",
        )
        from app.runs.service import mark_review_ready  # noqa: WPS433

        review_ready = mark_review_ready(str(created["run_id"]))
        self.assertEqual("review_ready", review_ready["phase"])

        resumed = resolve_lane_b_agent_run(
            workspace_id="workspace_alpha",
            content="Follow-up after review",
            linked_run_id=str(created["run_id"]),
            execution_access="full",
        )
        self.assertEqual(str(created["run_id"]), str(resumed["run_id"]))
        self.assertEqual("executing", resumed["phase"])

    def test_full_access_resumes_paused_linked_run(self) -> None:
        created = resolve_lane_b_agent_run(
            workspace_id="workspace_alpha",
            content="First turn",
            linked_run_id=None,
            execution_access="full",
        )
        paused = stop_run(str(created["run_id"]))
        self.assertEqual("paused", paused["phase"])

        resumed = resolve_lane_b_agent_run(
            workspace_id="workspace_alpha",
            content="Continue after stop",
            linked_run_id=str(created["run_id"]),
            execution_access="full",
        )
        self.assertEqual(str(created["run_id"]), str(resumed["run_id"]))
        self.assertEqual("executing", resumed["phase"])

    def test_consultative_resumes_review_ready_linked_run(self) -> None:
        created = resolve_lane_b_agent_run(
            workspace_id="workspace_alpha",
            content="First turn",
            linked_run_id=None,
            execution_access="consultative",
        )
        from app.runs.service import mark_review_ready  # noqa: WPS433

        review_ready = mark_review_ready(str(created["run_id"]))
        self.assertEqual("review_ready", review_ready["phase"])

        resumed = resolve_lane_b_agent_run(
            workspace_id="workspace_alpha",
            content="Follow-up after review",
            linked_run_id=str(created["run_id"]),
            execution_access="consultative",
        )
        self.assertEqual(str(created["run_id"]), str(resumed["run_id"]))
        self.assertEqual("executing", resumed["phase"])

    def test_consultative_resumes_paused_linked_run(self) -> None:
        created = resolve_lane_b_agent_run(
            workspace_id="workspace_alpha",
            content="First turn",
            linked_run_id=None,
            execution_access="consultative",
        )
        paused = stop_run(str(created["run_id"]))
        self.assertEqual("paused", paused["phase"])

        resumed = resolve_lane_b_agent_run(
            workspace_id="workspace_alpha",
            content="Continue after stop",
            linked_run_id=str(created["run_id"]),
            execution_access="consultative",
        )
        self.assertEqual(str(created["run_id"]), str(resumed["run_id"]))
        self.assertEqual("executing", resumed["phase"])


if __name__ == "__main__":
    unittest.main()
