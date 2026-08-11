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
from app.workspace_agents.config_loader import EmployeeConfig  # noqa: E402
from app.workspace_agents.scheduler import (  # noqa: E402
    kick_lead_fan_out_dispatch,
    run_continuous_worker_tick,
)
from app.workspace_agents.assignment_messages import assignment_card  # noqa: E402
from app.workspace_agents.scheduler_queued_fan_out import (  # noqa: E402
    dispatch_queued_lead_fan_out_runs,
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
                    side_effect=[
                        [{"run_id": "run_kicked", "phase": "executing"}],
                        [],
                    ],
                ) as mock_dispatch,
            ):
                kicked = kick_lead_fan_out_dispatch(starts_bound=2)
                tick = run_continuous_worker_tick()

        self.assertEqual(1, len(kicked))
        self.assertEqual("run_kicked", kicked[0]["run_id"])
        self.assertEqual(2, mock_dispatch.call_count)
        self.assertEqual(2, mock_dispatch.call_args_list[0].kwargs["starts_bound"])
        self.assertIsNone(mock_dispatch.call_args_list[0].kwargs["target_run_id"])
        self.assertEqual([], tick)

    def test_lead_assignment_card_uses_lead_action_language(self) -> None:
        card = assignment_card(
            assignee_name="Dana",
            assignee_role="lead",
            goal='Lead: advance "Ship canary" toward Done [plan lead-plan-demo]',
            task_id="task-demo123456789",
            run_id="run-demo",
            state="queued",
            lead_name="Dana",
        )

        self.assertIn("Lead should decide, assign, escalate, or report back", card)
        self.assertNotIn("specialist should implement", card)

    def test_paused_tick_rescues_queued_lead_handoff_after_restart(self) -> None:
        """Restarted Manual/Semi sessions must not strand Dana→specialist handoffs."""
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
                    return_value=[{"run_id": "run_priya", "phase": "executing"}],
                ) as mock_dispatch,
            ):
                tick = run_continuous_worker_tick()

        self.assertEqual([], tick)
        mock_dispatch.assert_called_once()
        self.assertEqual(2, mock_dispatch.call_args.kwargs["starts_bound"])
        self.assertIsNone(mock_dispatch.call_args.kwargs["target_run_id"])

    def test_kick_can_target_one_operator_started_run(self) -> None:
        with patch.dict(
            os.environ,
            {
                "AXON_WATCH_WORKER_SCHEDULER": "1",
                "AXON_WATCH_WORKER_SCHEDULER_DISPATCH": "1",
            },
            clear=False,
        ):
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
                    return_value=[{"run_id": "run_target", "phase": "executing"}],
                ) as mock_dispatch,
            ):
                kicked = kick_lead_fan_out_dispatch(
                    starts_bound=1,
                    target_run_id="run_target",
                )

        self.assertEqual("run_target", kicked[0]["run_id"])
        self.assertEqual(
            "run_target",
            mock_dispatch.call_args.kwargs["target_run_id"],
        )

    def test_queued_dispatch_filters_to_the_target_run(self) -> None:
        queued = [
            {
                "run_id": "run_other",
                "workspace_id": "workspace_demo",
                "employee_role": "backend",
                "task_id": "task_other",
                "phase": "queued",
                "started_at": "2026-07-30T14:00:02Z",
            },
            {
                "run_id": "run_target",
                "workspace_id": "workspace_demo",
                "employee_role": "frontend",
                "task_id": "task_target",
                "phase": "queued",
                "started_at": "2026-07-30T14:00:01Z",
            },
        ]
        with (
            patch(
                "app.workspace_agents.scheduler_queued_fan_out.worker_dispatch_enabled",
                return_value=True,
            ),
            patch(
                "app.workspace_agents.scheduler_queued_fan_out.list_runs",
                return_value=queued,
            ),
            patch(
                "app.workspace_agents.scheduler_queued_fan_out.begin_execution",
                side_effect=lambda run_id, **_kwargs: {
                    "run_id": run_id,
                    "phase": "executing",
                },
            ) as begin,
            patch.object(
                worker_scheduler_settings_store,
                "is_employee_enabled",
                return_value=True,
            ),
        ):
            started = dispatch_queued_lead_fan_out_runs(
                companies={"workspace_demo": object()},
                starts_bound=1,
                active_bound=3,
                executing_run_count=lambda: 0,
                employee_for_role=lambda *_args: EmployeeConfig(
                    name="Priya",
                    role="frontend",
                    owns="UI",
                    schedule="continuous",
                ),
                dispatch_worker_run=lambda **_kwargs: None,
                target_run_id="run_target",
            )

        self.assertEqual(["run_target"], [row["run_id"] for row in started])
        begin.assert_called_once()
        self.assertEqual("run_target", begin.call_args.args[0])

    def test_queued_fan_out_skips_when_same_role_already_executing(self) -> None:
        runs = [
            {
                "run_id": "run_lead_busy",
                "workspace_id": "workspace_demo",
                "employee_role": "lead",
                "task_id": "task_busy",
                "phase": "executing",
                "started_at": "2026-07-30T13:00:00Z",
            },
            {
                "run_id": "run_lead_queued",
                "workspace_id": "workspace_demo",
                "employee_role": "lead",
                "task_id": "task_queued",
                "phase": "queued",
                "started_at": "2026-07-30T14:00:00Z",
            },
        ]
        with (
            patch(
                "app.workspace_agents.scheduler_queued_fan_out.worker_dispatch_enabled",
                return_value=True,
            ),
            patch(
                "app.workspace_agents.scheduler_queued_fan_out.list_runs",
                return_value=runs,
            ),
            patch(
                "app.workspace_agents.scheduler_queued_fan_out.begin_execution",
            ) as begin,
            patch.object(
                worker_scheduler_settings_store,
                "is_employee_enabled",
                return_value=True,
            ),
        ):
            started = dispatch_queued_lead_fan_out_runs(
                companies={"workspace_demo": object()},
                starts_bound=2,
                active_bound=4,
                executing_run_count=lambda: 1,
                employee_for_role=lambda *_args: EmployeeConfig(
                    name="Mira",
                    role="lead",
                    owns="Lead",
                    schedule="on_demand",
                ),
                dispatch_worker_run=lambda **_kwargs: None,
            )

        self.assertEqual(started, [])
        begin.assert_not_called()


if __name__ == "__main__":
    unittest.main()
