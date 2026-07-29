from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.persistence import run_store, worker_scheduler_settings_store  # noqa: E402
from app.workspace_agents.scheduler import (  # noqa: E402
    kick_lead_fan_out_dispatch,
    run_continuous_worker_tick,
)


class LeadFanOutDispatchKickTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)

    def test_kick_lead_fan_out_dispatch_works_when_scheduler_paused(self) -> None:
        """Operator Lead Send must start specialists even in semi/manual."""
        with patch.dict(
            os.environ,
            {
                "AXON_WATCH_WORKER_SCHEDULER": "1",
                "AXON_WATCH_WORKER_SCHEDULER_DISPATCH": "1",
            },
            clear=False,
        ):
            worker_scheduler_settings_store.patch_settings({"scheduler_enabled": False})
            with (
                patch(
                    "app.workspace_agents.scheduler.load_workspace_agent_configs",
                    return_value=({}, {}, {"workspace_demo": object()}, {}),
                ),
                patch(
                    "app.workspace_agents.scheduler._executing_run_count",
                    return_value=0,
                ),
                patch(
                    "app.workspace_agents.scheduler.max_active_executing",
                    return_value=3,
                ),
                patch(
                    "app.workspace_agents.scheduler._dispatch_queued_lead_fan_out_runs",
                    return_value=[{"run_id": "run_kicked", "phase": "executing"}],
                ) as mock_dispatch,
            ):
                kicked = kick_lead_fan_out_dispatch(starts_bound=2)
                tick = run_continuous_worker_tick()

        self.assertEqual(1, len(kicked))
        self.assertEqual("run_kicked", kicked[0]["run_id"])
        mock_dispatch.assert_called_once()
        self.assertEqual(2, mock_dispatch.call_args.kwargs["starts_bound"])
        self.assertEqual([], tick)


if __name__ == "__main__":
    unittest.main()
