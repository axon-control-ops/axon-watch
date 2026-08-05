"""Unit tests for Axon-owned agent terminal jobs."""

from __future__ import annotations

import time
import unittest

from tests.support.control_plane_db import isolate_control_plane_db


class AgentTerminalJobsTests(unittest.TestCase):
    def setUp(self) -> None:
        from app.persistence import chat_store, run_store
        from app.chat.chat_stream_defer import reset_deferred_chat_streams
        from app.terminal.active_chat_stream import reset_active_chat_streams
        from app.terminal.agent_job_chat import reset_live_job_fences
        from app.terminal.agent_jobs import reset_agent_terminal_jobs
        from app.terminal.session_registry import reset_registry
        from app.terminal.session_runtime import reset_runtimes

        isolate_control_plane_db(self, run_store)
        chat_store.reset_store()
        reset_registry()
        reset_runtimes()
        reset_agent_terminal_jobs()
        reset_active_chat_streams()
        reset_live_job_fences()
        reset_deferred_chat_streams()
        self.addCleanup(reset_agent_terminal_jobs)
        self.addCleanup(reset_live_job_fences)
        self.addCleanup(reset_deferred_chat_streams)
        self.addCleanup(reset_active_chat_streams)
        self.addCleanup(reset_runtimes)
        self.addCleanup(reset_registry)
        self.addCleanup(chat_store.reset_store)

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
        self.assertFalse(job.get("stream_to_chat"))
        self.assertEqual(1, len(list_agent_terminal_jobs("workspace_axon_watch")))

    def test_enqueue_rejects_foreign_dashpro_ship_command(self) -> None:
        from app.terminal.agent_jobs import enqueue_agent_terminal_job
        from app.terminal.ship_command_guards import ShipCommandGuardError

        with self.assertRaises(ShipCommandGuardError):
            enqueue_agent_terminal_job(
                workspace_id="workspace_dashpro",
                source_workspace_id="workspace_young_eagles_day_care",
                command="npm run ota:canary",
                run_id="run_foreign_ship",
            )

    def test_stream_to_chat_tees_pty_chunks_into_open_fence(self) -> None:
        from app.persistence import chat_store
        from app.terminal.active_chat_stream import register_active_chat_stream
        from app.terminal.agent_jobs import enqueue_agent_terminal_job, get_agent_terminal_job

        thread = chat_store.create_thread(
            workspace_id="workspace_axon_watch",
            run_id="run_stream_job",
            created_at="2026-07-30T00:00:00Z",
            thread_kind="ide",
            title="stream job",
        )
        message = chat_store.save_message(
            {
                "message_id": "message_agent_stream",
                "thread_id": thread["thread_id"],
                "workspace_id": "workspace_axon_watch",
                "run_id": "run_stream_job",
                "role": "agent",
                "content": "Working…\n",
                "created_at": "2026-07-30T00:00:00Z",
            }
        )
        register_active_chat_stream(
            workspace_id="workspace_axon_watch",
            thread_id=thread["thread_id"],
            message_id=message["message_id"],
            run_id="run_stream_job",
        )

        job = enqueue_agent_terminal_job(
            workspace_id="workspace_axon_watch",
            command="printf 'hello-live\\n'; sleep 0.05; printf 'bye-live\\n'",
            run_id="run_stream_job",
            stream_to_chat=True,
        )
        self.assertTrue(job.get("stream_to_chat"))
        self.assertEqual(message["message_id"], job.get("message_id"))

        deadline = time.time() + 8.0
        content = ""
        while time.time() < deadline:
            row = chat_store.get_message(message["message_id"])
            content = str((row or {}).get("content") or "")
            if "hello-live" in content and "# axon-job:" in content:
                break
            time.sleep(0.05)

        self.assertIn(":::terminal", content)
        self.assertIn("hello-live", content)

        deadline = time.time() + 8.0
        while time.time() < deadline:
            row = chat_store.get_message(message["message_id"])
            content = str((row or {}).get("content") or "")
            record = get_agent_terminal_job(str(job["job_id"]))
            if "[exit" in content or (record and record.get("status") != "running"):
                break
            time.sleep(0.05)

        self.assertIn("bye-live", content)
        self.assertIn("[exit", content)


if __name__ == "__main__":
    unittest.main()

