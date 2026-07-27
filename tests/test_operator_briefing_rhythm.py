from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.operator_briefing_rhythm import (  # noqa: E402
    build_briefing_advise,
    build_briefing_decide,
    build_briefing_execute,
    build_briefing_notice,
    build_briefing_report,
    build_briefing_verify,
    build_operator_briefing_rhythm,
)


class OperatorBriefingRhythmTests(unittest.TestCase):
    def test_notice_prioritizes_pending_approvals(self) -> None:
        notice = build_briefing_notice(
            active_runs=[{"phase": "awaiting_approval", "title": "Guarded run"}],
            top_signals=[{"title": "Signal", "severity": "high"}],
            pending_approvals_count=2,
            degraded={"active": False, "reasons": []},
            watch_connected=True,
        )

        self.assertEqual("2 runs awaiting explicit approval.", notice)

    def test_notice_surfaces_review_ready_run(self) -> None:
        notice = build_briefing_notice(
            active_runs=[{"phase": "review_ready", "title": "Smoke run", "run_id": "run_smoke"}],
            top_signals=[],
            pending_approvals_count=0,
            degraded={"active": False, "reasons": []},
            watch_connected=True,
        )

        self.assertEqual("Smoke run is ready for your review.", notice)

    def test_notice_surfaces_lead_awaiting_engagement(self) -> None:
        notice = build_briefing_notice(
            active_runs=[],
            top_signals=[],
            pending_approvals_count=0,
            degraded={"active": False, "reasons": []},
            watch_connected=True,
            lead_awaiting_engagement_count=1,
        )

        self.assertEqual("1 Lead plan awaiting engagement in VAXON.", notice)

    def test_idle_rhythm_stays_quiet_instead_of_inventing_status_copy(self) -> None:
        rhythm = build_operator_briefing_rhythm(
            active_runs=[],
            top_signals=[],
            pending_approvals_count=0,
            degraded={"active": False, "reasons": []},
            watch_connected=True,
            next_safe_actions=[],
        )

        self.assertEqual("", rhythm["notice"])
        self.assertEqual("", rhythm["advise"])
        self.assertEqual("", rhythm["decide"])
        self.assertEqual("", rhythm["execute"])
        self.assertEqual("", rhythm["verify"])
        self.assertEqual("", rhythm["report"])

    def test_notice_uses_live_signal_instead_of_idle_copy(self) -> None:
        notice = build_briefing_notice(
            active_runs=[],
            top_signals=[{"title": "Fast Gate failed", "severity": "high"}],
            pending_approvals_count=0,
            degraded={"active": False, "reasons": []},
            watch_connected=True,
        )

        self.assertEqual("High-priority signal: Fast Gate failed.", notice)

    def test_advise_uses_first_next_safe_action(self) -> None:
        advise = build_briefing_advise(
            next_safe_actions=[
                {
                    "action_id": "approve_run_test",
                    "kind": "approve_run",
                    "title": "Approve guarded run",
                    "detail": "Approve Smoke run to continue execution.",
                }
            ],
            active_runs=[],
        )

        self.assertEqual("Approve Smoke run to continue execution.", advise)

    def test_rhythm_bundle_is_additive(self) -> None:
        rhythm = build_operator_briefing_rhythm(
            active_runs=[{"phase": "review_ready", "title": "Smoke run"}],
            top_signals=[],
            pending_approvals_count=0,
            degraded={"active": False, "reasons": []},
            watch_connected=True,
            next_safe_actions=[
                {
                    "action_id": "resume_run_test",
                    "kind": "resume_run",
                    "title": "Resume paused run",
                    "detail": "Resume Smoke run.",
                }
            ],
        )

        self.assertEqual({"notice", "advise", "decide", "execute", "verify", "report"}, set(rhythm))
        self.assertIn("review", rhythm["notice"])
        self.assertIn("Resume Smoke run.", rhythm["advise"])
        self.assertIn("Decide whether to resume", rhythm["decide"])
        self.assertIn("Execute:", rhythm["execute"])
        self.assertIn("Verify", rhythm["verify"])
        self.assertIn("Report:", rhythm["report"])

    def test_decide_prioritizes_pending_approvals(self) -> None:
        decide = build_briefing_decide(
            pending_approvals_count=1,
            active_runs=[],
            top_signals=[{"title": "Signal", "severity": "high"}],
            degraded={"active": False, "reasons": []},
        )
        self.assertIn("approve or reject", decide.lower())

    def test_execute_maps_next_safe_action_kind(self) -> None:
        execute = build_briefing_execute(
            next_safe_actions=[{"kind": "approve_run", "title": "Approve guarded run"}],
        )
        self.assertIn("approve the guarded run", execute.lower())

    def test_report_summarizes_canonical_counts(self) -> None:
        report = build_briefing_report(
            pending_approvals_count=2,
            top_signals=[{"title": "A"}, {"title": "B"}],
            active_runs=[{"phase": "executing"}],
            degraded={"active": True, "reasons": ["watch probe failed"]},
        )
        self.assertIn("2 pending approvals", report)
        self.assertIn("2 surfaced signals", report)
        self.assertIn("runtime degraded", report)


if __name__ == "__main__":
    unittest.main()
