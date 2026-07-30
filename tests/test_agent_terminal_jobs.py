"""Unit tests for Axon-owned agent terminal jobs."""

from __future__ import annotations

import unittest

from tests.support.control_plane_db import isolate_control_plane_db


class AgentTerminalJobsTests(unittest.TestCase):
    def setUp(self) -> None:
        from app.persistence import run_store
        from app.terminal.agent_jobs import reset_agent_terminal_jobs
        from app.terminal.session_registry import reset_registry
        from app.terminal.session_runtime import reset_runtimes

        isolate_control_plane_db(self, run_store)
        reset_registry()
        reset_runtimes()
        reset_agent_terminal_jobs()
        self.addCleanup(reset_agent_terminal_jobs)
        self.addCleanup(reset_runtimes)
        self.addCleanup(reset_registry)

    def test_enqueue_writes_to_agent_pty_and_returns_receipt(self) -> None:
        from app.terminal.agent_jobs import enqueue_agent_terminal_job, list_agent_terminal_jobs

        job = enqueue_agent_terminal_job(
            workspace_id="workspace_axon_watch",
            command="echo axon-job-ok",
            run_id="run_test_job",
        )
        self.assertTrue(str(job["job_id"]).startswith("agent-job-"))
        self.assertEqual("terminal-agent", job["session_id"])
        self.assertEqual("echo axon-job-ok", job["command"])
        self.assertEqual("running", job["status"])
        self.assertIn("Running in Axon terminal", job["receipt"])
        self.assertEqual(1, len(list_agent_terminal_jobs("workspace_axon_watch")))


if __name__ == "__main__":
    unittest.main()
