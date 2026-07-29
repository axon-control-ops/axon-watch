"""Run-outcome selection when Critical Review confidence is missing or recovered."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.persistence import run_store  # noqa: E402
from app.runs.service import complete_run, create_run, fail_run  # noqa: E402
from app.workspace_agents.run_outcome import latest_role_run_outcome  # noqa: E402


class RunOutcomeConfidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)

    def test_missing_confidence_failure_yields_to_same_stamp_completed(self) -> None:
        failed = create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Priya: continuous worker shift",
            employee_role="frontend",
        )
        fail_run(
            failed["run_id"],
            receipt_summary=(
                "Critical Review Clause missing: final reply must end with "
                "Confidence: N/10 (integer 1-10) after the rewritten summary."
            ),
        )
        failed_row = run_store.get_run(failed["run_id"])
        assert failed_row is not None
        stamp = str(failed_row.get("updated_at") or "")

        completed = create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Priya: IDE retry with confidence",
            employee_role="frontend",
        )
        complete_run(completed["run_id"])
        completed_row = run_store.get_run(completed["run_id"])
        assert completed_row is not None
        completed_row["updated_at"] = stamp
        run_store.save_run(completed_row)

        outcome = latest_role_run_outcome("workspace_axon_watch", "frontend")
        assert outcome is not None
        self.assertEqual("completed", outcome["outcome"])
        self.assertEqual(completed["run_id"], outcome["run_id"])

    def test_newer_missing_confidence_still_surfaces_over_older_completed(self) -> None:
        completed = create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Priya: earlier success",
            employee_role="frontend",
        )
        complete_run(completed["run_id"])
        completed_row = run_store.get_run(completed["run_id"])
        assert completed_row is not None
        completed_row["updated_at"] = "2026-07-01T10:00:00Z"
        run_store.save_run(completed_row)

        failed = create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Priya: later confidence miss",
            employee_role="frontend",
        )
        fail_run(
            failed["run_id"],
            receipt_summary=(
                "Critical Review Clause missing: final reply must end with "
                "Confidence: N/10 (integer 1-10) after the rewritten summary."
            ),
        )
        failed_row = run_store.get_run(failed["run_id"])
        assert failed_row is not None
        failed_row["updated_at"] = "2026-07-28T06:00:00Z"
        run_store.save_run(failed_row)

        outcome = latest_role_run_outcome("workspace_axon_watch", "frontend")
        assert outcome is not None
        self.assertEqual("failed", outcome["outcome"])
        self.assertEqual(failed["run_id"], outcome["run_id"])
        self.assertIn("Critical Review Clause missing", outcome["detail"])


if __name__ == "__main__":
    unittest.main()
