from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.operator_briefing_rhythm import (  # noqa: E402
    build_briefing_advise,
    build_briefing_notice,
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

        self.assertEqual("Smoke run is ready for operator review.", notice)

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

        self.assertEqual({"notice", "advise"}, set(rhythm))
        self.assertIn("review", rhythm["notice"])
        self.assertIn("Resume Smoke run.", rhythm["advise"])


if __name__ == "__main__":
    unittest.main()
