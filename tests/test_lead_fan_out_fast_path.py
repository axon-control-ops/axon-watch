from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.chat.lane_b_lead_fan_out_fast_path import (  # noqa: E402
    maybe_post_lead_fan_out_message,
)


class LeadFanOutFastPathTests(unittest.TestCase):
    def test_plan_mode_materializes_implementation_fan_out(self) -> None:
        saved: list[dict] = []
        prompt = "Assign all agents to start working on the Expo native companion app"
        materialize = {
            "plan_id": "plan_team",
            "mode": "fan_out",
            "tasks": [{"owner_role": "frontend", "goal": prompt}],
            "runs": [{"run_id": "run_jules", "owner_role": "frontend"}],
            "deferred": [],
            "receipt": {"summary": "Materialized team fan-out"},
        }
        handoff = {"run_id": "run_lead_handoff", "phase": "completed", "employee_role": "lead"}

        with (
            patch(
                "app.chat.lane_b_lead_fan_out_fast_path.materialize_lead_fan_out",
                return_value=materialize,
            ) as materialize_call,
            patch(
                "app.chat.lane_b_lead_fan_out_fast_path.record_lead_handoff_run",
                return_value=handoff,
            ),
            patch(
                "app.chat.lane_b_lead_fan_out_fast_path._kick_continuous_dispatch",
                return_value=1,
            ),
        ):
            response = maybe_post_lead_fan_out_message(
                workspace_id="workspace_axon_watch",
                content=prompt,
                thread_id="thread_lead",
                employee_role="lead",
                lead_name="Mira",
                composer_mode="plan",
                created_at="2026-08-23T21:00:00Z",
                save_message=lambda payload: saved.append(payload) or payload,
                new_message_id=lambda prefix: f"{prefix}_1",
                bind_attachments=lambda _message_id: [],
            )

        self.assertIsNotNone(response)
        assert response is not None
        self.assertTrue(response["dispatched"])
        self.assertEqual("run_lead_handoff", response["run_id"])
        self.assertEqual("plan_team", response["lead_fan_out"]["plan_id"])
        materialize_call.assert_called_once()
        self.assertEqual("fan_out", materialize_call.call_args.kwargs["mode"])
        self.assertTrue(materialize_call.call_args.kwargs["create_runs"])

    def test_plan_mode_status_fan_out_stays_consultative(self) -> None:
        with patch(
            "app.chat.lane_b_lead_fan_out_fast_path.materialize_lead_fan_out",
        ) as materialize_call:
            response = maybe_post_lead_fan_out_message(
                workspace_id="workspace_axon_watch",
                content="Ask every teammate for a status before I decide",
                thread_id="thread_lead",
                employee_role="lead",
                lead_name="Mira",
                composer_mode="plan",
                created_at="2026-08-23T21:00:00Z",
                save_message=lambda payload: payload,
                new_message_id=lambda prefix: f"{prefix}_1",
                bind_attachments=lambda _message_id: [],
            )

        self.assertIsNone(response)
        materialize_call.assert_not_called()


if __name__ == "__main__":
    unittest.main()
