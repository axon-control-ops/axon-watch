from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.workspace_agents.status import employee_status  # noqa: E402


class WorkspaceAgentStatusTests(unittest.TestCase):
    def test_lead_reflects_role_tagged_run(self) -> None:
        self.assertEqual(
            "executing",
            employee_status(
                role="lead",
                schedule="on_demand",
                workspace_status="idle",
                primary=True,
                role_run_status="executing",
            ),
        )
        self.assertEqual(
            "assigned",
            employee_status(
                role="lead",
                schedule="on_demand",
                workspace_status="idle",
                primary=True,
                role_run_status="assigned",
            ),
        )


if __name__ == "__main__":
    unittest.main()
