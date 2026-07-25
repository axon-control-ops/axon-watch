"""Debug composer mode creates debug-labeled Lane B runs."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.chat.lane_b_run_dispatch import resolve_lane_b_agent_run  # noqa: E402


class LaneBDebugRunDispatchTests(unittest.TestCase):
    @patch("app.chat.lane_b_run_dispatch.create_run")
    def test_debug_composer_mode_creates_debug_run(self, mock_create) -> None:
        mock_create.return_value = {"run_id": "run_debug", "mode": "debug"}
        result = resolve_lane_b_agent_run(
            workspace_id="workspace_axon_watch",
            content="Button does nothing on click",
            linked_run_id=None,
            execution_access="full",
            composer_mode="debug",
        )
        self.assertEqual(result["run_id"], "run_debug")
        kwargs = mock_create.call_args.kwargs
        self.assertEqual(kwargs["mode"], "debug")
        self.assertIn("debug", kwargs["detail"].lower())

    @patch("app.chat.lane_b_run_dispatch.create_run")
    def test_agent_composer_mode_creates_agent_run(self, mock_create) -> None:
        mock_create.return_value = {"run_id": "run_agent", "mode": "agent"}
        resolve_lane_b_agent_run(
            workspace_id="workspace_axon_watch",
            content="Add a feature",
            linked_run_id=None,
            execution_access="full",
            composer_mode="agent",
        )
        self.assertEqual(mock_create.call_args.kwargs["mode"], "agent")

    @patch("app.chat.lane_b_run_dispatch.create_run")
    @patch("app.chat.lane_b_run_dispatch.get_run")
    def test_debug_mode_does_not_resume_agent_run(self, mock_get, mock_create) -> None:
        mock_get.return_value = {
            "run_id": "run_agent_review",
            "workspace_id": "workspace_axon_watch",
            "mode": "agent",
            "phase": "review_ready",
        }
        mock_create.return_value = {"run_id": "run_debug_new", "mode": "debug"}
        result = resolve_lane_b_agent_run(
            workspace_id="workspace_axon_watch",
            content="Debug this crash",
            linked_run_id="run_agent_review",
            execution_access="full",
            composer_mode="debug",
        )
        self.assertEqual(result["run_id"], "run_debug_new")
        self.assertEqual(mock_create.call_args.kwargs["mode"], "debug")


if __name__ == "__main__":
    unittest.main()
