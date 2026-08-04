"""Executive Lead report normalization."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.workspace_agents.lead_executive_brief import (  # noqa: E402
    compress_ask,
    executive_next_step,
    executive_operator_action,
    plain_outcome,
)
from app.workspace_agents.lead_text import truncate_text  # noqa: E402


class LeadExecutiveBriefTests(unittest.TestCase):
    def test_truncation_never_leaves_single_letter_fragment(self) -> None:
        shortened = truncate_text(
            "Can we check how many parents responded and implement another feature",
            max_len=48,
        )
        self.assertTrue(shortened.endswith("…"))
        self.assertNotRegex(shortened, r"\s[A-Za-z]…$")

    def test_worker_envelope_is_removed_from_situation(self) -> None:
        ask = compress_ask(
            "Continuous worker dispatch started. Role, lead. Task, task-1. "
            "Run, run-1. Goal, Lead: advance Can we check parent counts and uploads?"
        )
        self.assertEqual("Can we check parent counts and uploads?", ask)

    def test_runtime_protocol_becomes_plain_failure(self) -> None:
        outcome = plain_outcome(
            "Lane B agent could not start on Codex; type thread.started; thread id 019fcb3e."
        )
        self.assertEqual(
            "The agent attempt failed before work started; no verified result landed.",
            outcome,
        )

    def test_shell_chore_stays_with_lead(self) -> None:
        next_step = executive_next_step(
            lead_next="Run from project root with .env and npm run graduation-card-pop-counts",
            specialist_name="Cole",
            parent_ask="Count responses",
            status="completed",
        )
        self.assertIn("I will finish the verification", next_step)
        self.assertNotIn("npm run", next_step)

    def test_parent_pop_goal_becomes_plain_executive_language(self) -> None:
        ask = compress_ask(
            "Can we check how many parents responded on graduation cards and uploaded POP? "
            "Also implement chat-sent proof of payment as an upload."
        )
        self.assertEqual(
            "Count parent graduation-card responses and payment proofs, then make "
            "chat-sent proof visible to parents and centre staff.",
            ask,
        )

    def test_internal_watcher_cleanup_never_becomes_operator_work(self) -> None:
        reply = (
            "I cleared the failed shift. Root cause was a stale-timeout reap after "
            "794s idle against the 720s watcher cutoff."
        )
        outcome = plain_outcome(reply)
        self.assertIn("sitting idle too long", outcome)
        self.assertNotIn("794", outcome)
        self.assertNotIn("stale", outcome.lower())

        internal_next = (
            "Accept clearance for dedupe "
            "failed_shift:workspace_young_eagles_day_care:watcher:run_145d05acc77a"
        )
        next_step = executive_next_step(
            lead_next=internal_next,
            specialist_name="Ash",
            parent_ask=(
                "Count parent graduation-card responses and payment proofs, then make "
                "chat-sent proof visible to parents and centre staff."
            ),
            status="completed",
        )
        self.assertIn("verified counts", next_step)
        self.assertNotIn("dedupe", next_step)
        self.assertIn("Nothing right now", executive_operator_action(internal_next))


if __name__ == "__main__":
    unittest.main()
