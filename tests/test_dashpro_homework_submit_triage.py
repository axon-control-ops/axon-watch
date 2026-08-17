"""DashPro homework submit triage prompt clause."""

from __future__ import annotations

import unittest

import sys
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.workspace_agents.dashpro_homework_submit_triage import (  # noqa: E402
    dashpro_homework_submit_triage_clause,
)


class DashproHomeworkSubmitTriageTests(unittest.TestCase):
    def test_clause_covers_rls_and_check_layers(self) -> None:
        clause = dashpro_homework_submit_triage_clause()
        self.assertIn("row-level security policy", clause)
        self.assertIn("homework_submissions_content_type_check", clause)
        self.assertIn("homework_submissions_submission_type_check", clause)
        self.assertIn("resolveHomeworkSubmissionTypes", clause)
        self.assertIn("do not run supabase db push", clause.lower())


if __name__ == "__main__":
    unittest.main()
