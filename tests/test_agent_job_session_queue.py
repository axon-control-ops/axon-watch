from __future__ import annotations

import sys
import threading
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.terminal.agent_job_session_queue import (  # noqa: E402
    enqueue_session_job,
    notify_session_job_finished,
)


class AgentJobSessionQueueTests(unittest.TestCase):
    def test_serializes_jobs_on_same_session(self) -> None:
        order: list[str] = []
        first_started = threading.Event()
        release_first = threading.Event()
        second_done = threading.Event()

        def first() -> None:
            order.append("first-start")
            first_started.set()
            release_first.wait(timeout=2)
            order.append("first-end")
            notify_session_job_finished(workspace_id="ws", session_id="terminal-agent")

        def second() -> None:
            order.append("second-start")
            notify_session_job_finished(workspace_id="ws", session_id="terminal-agent")
            second_done.set()

        worker = threading.Thread(
            target=lambda: enqueue_session_job(
                workspace_id="ws",
                session_id="terminal-agent",
                dispatch=first,
            ),
            daemon=True,
        )
        worker.start()
        self.assertTrue(first_started.wait(timeout=1))
        self.assertEqual(["first-start"], order)

        enqueue_session_job(workspace_id="ws", session_id="terminal-agent", dispatch=second)
        release_first.set()
        self.assertTrue(second_done.wait(timeout=2))
        self.assertEqual(["first-start", "first-end", "second-start"], order)


if __name__ == "__main__":
    unittest.main()
