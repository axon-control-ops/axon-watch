from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.persistence import run_store  # noqa: E402
from app.workspace_agents.lead_handoff_receipt import record_lead_handoff_run  # noqa: E402
from app.workspace_agents.run_outcome import latest_role_run_outcome  # noqa: E402
from app.runs.service import create_run, fail_run  # noqa: E402


class LeadHandoffReceiptTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)

    def test_handoff_receipt_clears_prior_lead_failure_outcome(self) -> None:
        failed = create_run(
            workspace_id="workspace_dashpro",
            mode="agent",
            summary="Prior Lead shift",
            employee_role="lead",
        )
        fail_run(failed["run_id"], receipt_summary="Critical Review Clause missing")
        prior = latest_role_run_outcome("workspace_dashpro", "lead")
        self.assertIsNotNone(prior)
        assert prior is not None
        self.assertEqual("failed", prior.get("outcome"))

        handoff = record_lead_handoff_run(
            workspace_id="workspace_dashpro",
            summary="Fix payments visibility across frontend and backend",
            detail="Lead decompose handoff completed; specialists queued",
        )
        self.assertIsNotNone(handoff)
        assert handoff is not None
        self.assertEqual("completed", handoff.get("phase"))
        self.assertEqual("lead", handoff.get("employee_role"))

        latest = latest_role_run_outcome("workspace_dashpro", "lead")
        self.assertIsNotNone(latest)
        assert latest is not None
        self.assertEqual("completed", latest.get("outcome"))
        self.assertEqual(handoff["run_id"], latest.get("run_id"))

    def test_handoff_receipt_survives_lifecycle_errors(self) -> None:
        with patch(
            "app.runs.service.create_run",
            side_effect=RuntimeError("boom"),
        ):
            self.assertIsNone(
                record_lead_handoff_run(
                    workspace_id="workspace_dashpro",
                    summary="anything",
                    detail="detail",
                )
            )


if __name__ == "__main__":
    unittest.main()
