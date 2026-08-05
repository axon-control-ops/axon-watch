"""Spoken Lead takeover / synthesis lines."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.workspace_agents.lead_takeover_voice import (  # noqa: E402
    build_lead_shift_spoken_line,
    build_lead_synthesis_spoken_line,
    build_lead_takeover_spoken_line,
    emit_lead_spoken_line,
)


class LeadTakeoverVoiceTests(unittest.TestCase):
    def test_takeover_spoken_line_includes_specialist_and_lead_read(self) -> None:
        line = build_lead_takeover_spoken_line(
            employee_name="Soren",
            employee_role="integrations",
            phase="completed",
            reply_text=(
                "Sir King — OTA gate blocked. Wrong branch and dirty tree.\n"
                "Blockers / Lead next: Lead: hold OTA; merge when green.\n"
                "Confidence: 8/10"
            ),
            lead_name="Dana",
        )
        self.assertIn("Dana here", line)
        self.assertIn("Soren (integrations) completed", line)
        self.assertIn("Progress:", line)
        self.assertIn("What remains:", line)
        self.assertIn("What I am doing next:", line)
        self.assertIn("Your action:", line)
        self.assertIn("hold OTA", line)
        self.assertNotIn("Specialist report:", line)
        self.assertNotIn("Ask me what to do next", line)
        self.assertNotIn("Confidence:", line)

    def test_takeover_spoken_line_names_parent_ask_first(self) -> None:
        line = build_lead_takeover_spoken_line(
            employee_name="Cass",
            employee_role="watcher",
            phase="completed",
            reply_text=(
                "Payments contract check failed.\n"
                "Lead: open Marco for contract coverage.\n"
                "Confidence: 9/10"
            ),
            lead_name="Dana",
            parent_plan_goal="Push OTA to canary",
        )
        self.assertIn("Goal: Push OTA to canary", line)
        self.assertIn("What I am doing next:", line)
        self.assertLess(
            line.index("Goal:"),
            line.index("Cass (watcher) completed"),
        )
        self.assertNotIn("Ask me what to do next", line)
        self.assertNotIn("Confidence:", line)

    def test_synthesis_spoken_line_lists_specialists(self) -> None:
        line = build_lead_synthesis_spoken_line(
            goal="Ship payments card",
            summary="Two specialists finished; one failed.",
            findings=[
                {
                    "assignee_name": "Priya",
                    "owner_role": "frontend",
                    "status": "completed",
                    "specialist_reply_excerpt": "Card restored.",
                },
                {
                    "assignee_name": "Marco",
                    "owner_role": "backend",
                    "status": "failed",
                    "specialist_reply_excerpt": "API 500.",
                },
            ],
            lead_name="Dana",
        )
        self.assertIn("Dana here", line)
        self.assertIn("Priya completed", line)
        self.assertIn("Marco failed", line)

    def test_lead_shift_spoken_line(self) -> None:
        line = build_lead_shift_spoken_line(
            employee_name="Dana",
            phase="completed",
            reply_text="Assigned Cass next.\nLead: wait for operator Decide.\nConfidence: 8/10",
        )
        self.assertIn("Dana here", line)
        self.assertIn("Lead shift just completed", line)
        self.assertIn("Next:", line)
        self.assertNotIn("Ask me what to do next", line)
        self.assertNotIn("Confidence:", line)

    @patch("app.live_events.broadcast_spoken_line", return_value=1)
    @patch(
        "app.workspace_agents.lead_takeover_voice._lead_speaker",
        return_value={
            "speaker_name": "Dana",
            "speaker_role": "lead",
            "speaker_employee_id": "employee-lead",
        },
    )
    def test_emit_broadcasts_spoken_line(self, _speaker, broadcast) -> None:
        result = emit_lead_spoken_line(
            workspace_id="workspace_dashpro",
            line="Dana here. Rollup ready.",
            receipt_id="lead_takeover_voice_run_1",
            kind="lead_takeover",
        )
        self.assertEqual("broadcast", result.get("status"))
        broadcast.assert_called_once()
        kwargs = broadcast.call_args.kwargs
        self.assertEqual("Dana here. Rollup ready.", kwargs["line"])
        self.assertEqual("employee-lead", kwargs["speaker_employee_id"])


if __name__ == "__main__":
    unittest.main()
