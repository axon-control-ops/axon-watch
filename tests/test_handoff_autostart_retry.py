from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.persistence import handoff_store, run_store, task_store  # noqa: E402
from app.workspace_agents.handoff_autostart_retry import (  # noqa: E402
    retry_pending_handoff_autostarts,
)


class HandoffAutostartRetryTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)
        task_store.reset_store()
        handoff_store.reset_store()
        self.addCleanup(task_store.reset_store)
        self.addCleanup(handoff_store.reset_store)

    def test_retries_open_follow_through_target_tasks(self) -> None:
        task = task_store.create_task(
            workspace_id="workspace_dashpro",
            goal="Fix avatar from YE handoff",
            acceptance_criteria="Complete the cross-workspace handoff from Young Eagles.",
            owner_role="frontend",
        )
        handoff = handoff_store.create_handoff_record(
            source_workspace_id="workspace_young_eagles_day_care",
            target_workspace_id="workspace_dashpro",
            task="Fix avatar",
            reason="App UI",
        )
        handoff_store.update_handoff(
            str(handoff["handoff_id"]),
            status="routed",
            target_task_id=str(task["task_id"]),
            routed_role="frontend",
        )

        with patch(
            "app.workspace_handoff_routing.try_autostart_handoff_task",
            return_value={
                "status": "started",
                "run_id": "run_retry_1",
                "detail": "started (executing)",
            },
        ) as autostart:
            advanced = retry_pending_handoff_autostarts(starts_bound=2)

        self.assertEqual(1, len(advanced))
        self.assertEqual(str(task["task_id"]), advanced[0]["task_id"])
        self.assertEqual("started", advanced[0]["status"])
        autostart.assert_called_once_with(str(task["task_id"]))

    def test_skips_when_autostart_still_waiting(self) -> None:
        task = task_store.create_task(
            workspace_id="workspace_dashpro",
            goal="Still blocked",
            owner_role="frontend",
        )
        handoff = handoff_store.create_handoff_record(
            source_workspace_id="workspace_young_eagles_day_care",
            target_workspace_id="workspace_dashpro",
            task="Still blocked",
        )
        handoff_store.update_handoff(
            str(handoff["handoff_id"]),
            status="routed",
            target_task_id=str(task["task_id"]),
        )

        with patch(
            "app.workspace_handoff_routing.try_autostart_handoff_task",
            return_value={
                "status": "waiting",
                "detail": 'teammate for role "frontend" already has active run',
            },
        ) as autostart:
            advanced = retry_pending_handoff_autostarts(starts_bound=2)

        self.assertEqual([], advanced)
        autostart.assert_called_once()
