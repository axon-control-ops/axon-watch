from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.persistence import (  # noqa: E402
    autonomous_attention_store,
    operator_presence_settings_store,
)
from app.workspace_agents.scheduler_attention_scan import (  # noqa: E402
    run_scheduled_autonomous_attention_scan,
)


class SchedulerAttentionScanTests(unittest.TestCase):
    def test_full_autonomy_runs_occasional_attention_scan(self) -> None:
        expected = {
            "checked_workspaces": ["workspace_dashpro"],
            "created_tasks": [],
        }
        with (
            patch(
                "app.workspace_agents.scheduler.scheduler_enabled",
                return_value=True,
            ),
            patch.object(
                operator_presence_settings_store,
                "load_settings",
                return_value={"autonomy_mode": "full"},
            ),
            patch.object(autonomous_attention_store, "get_meta", return_value={}),
            patch(
                "app.workspace_agents.autonomous_attention.run_autonomous_attention_scan",
                return_value=expected,
            ) as scan,
        ):
            result = run_scheduled_autonomous_attention_scan()

        self.assertEqual(expected, result)
        scan.assert_called_once_with(include_lead_checkin=False)

    def test_non_full_autonomy_does_not_scan(self) -> None:
        with (
            patch(
                "app.workspace_agents.scheduler.scheduler_enabled",
                return_value=True,
            ),
            patch.object(
                operator_presence_settings_store,
                "load_settings",
                return_value={"autonomy_mode": "semi"},
            ),
            patch(
                "app.workspace_agents.autonomous_attention.run_autonomous_attention_scan",
            ) as scan,
        ):
            self.assertIsNone(run_scheduled_autonomous_attention_scan())

        scan.assert_not_called()


if __name__ == "__main__":
    unittest.main()
