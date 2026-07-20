"""Roster outcome helpers expose real failure detail, not bare FAILED."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.persistence import run_store  # noqa: E402
from app.runs.service import create_run, fail_run  # noqa: E402
from app.workspace_agents.run_outcome import latest_role_run_outcome  # noqa: E402
from tests.support.control_plane_db import isolate_control_plane_db  # noqa: E402


class RunOutcomeTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)

    def test_fail_run_current_step_keeps_reason(self) -> None:
        created = create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Control Plane: continuous worker shift",
            employee_role="backend",
        )
        failed = fail_run(
            created["run_id"],
            receipt_summary="Lane B agent fallback reply generated (ActionRequiredError: out of usage)",
        )
        self.assertEqual("failed", failed["phase"])
        self.assertIn("out of usage", failed["current_step"])
        self.assertNotEqual("Run failed", failed["current_step"])

    def test_latest_role_outcome_reads_failure_receipt(self) -> None:
        created = create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Shell Craft: continuous worker shift",
            employee_role="frontend",
        )
        fail_run(
            created["run_id"],
            receipt_summary="Lane B agent fallback reply generated (ActionRequiredError: out of usage)",
        )
        outcome = latest_role_run_outcome("workspace_axon_watch", "frontend")
        assert outcome is not None
        self.assertEqual("failed", outcome["outcome"])
        self.assertIn("out of usage", outcome["detail"])


if __name__ == "__main__":
    unittest.main()
