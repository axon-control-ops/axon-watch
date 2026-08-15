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
        self.assertIn(job["status"], ("running", "completed"))
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
        record = get_agent_terminal_job(str(job["job_id"]))
        self.assertIsNotNone(record)
        assert record is not None
        self.assertIn("hello-live", str(record.get("output_tail") or ""))
        self.assertIn("bye-live", str(record.get("output_tail") or ""))

    def _await_terminal_status(self, job_id: str, *, timeout: float = 20.0) -> dict:
        from app.terminal.agent_jobs import get_agent_terminal_job

        deadline = time.time() + timeout
        record: dict = {}
        while time.time() < deadline:
            record = dict(get_agent_terminal_job(job_id) or {})
            if str(record.get("status") or "") not in ("", "running"):
                return record
            time.sleep(0.05)
        self.fail(f"job {job_id} never left running: {record}")

    def test_unstreamed_job_still_records_exit_code_and_output(self) -> None:
        """Regression: jobs with no chat target used to hang in `running` forever."""
        from app.terminal.agent_jobs import enqueue_agent_terminal_job

        job = enqueue_agent_terminal_job(
            workspace_id="workspace_axon_watch",
            command="printf 'quiet-job-ok\\n'",
            run_id="run_unstreamed_job",
        )
        self.assertFalse(job.get("stream_to_chat"))

        record = self._await_terminal_status(str(job["job_id"]))
        self.assertEqual("completed", record.get("status"))
        self.assertEqual(0, record.get("exit_code"))
        self.assertIn("quiet-job-ok", str(record.get("output_tail") or ""))

    def test_failing_unstreamed_job_reports_failed_status(self) -> None:
        from app.terminal.agent_jobs import enqueue_agent_terminal_job

        job = enqueue_agent_terminal_job(
            workspace_id="workspace_axon_watch",
            command="printf 'boom\\n' >&2; exit 3",
            run_id="run_failing_job",
        )
        record = self._await_terminal_status(str(job["job_id"]))
        self.assertEqual("failed", record.get("status"))
        self.assertEqual(3, record.get("exit_code"))

    def test_concurrent_jobs_do_not_steal_each_others_exit_codes(self) -> None:
        """Job-scoped sentinels keep two jobs on the shared PTY independent."""
        from app.terminal.agent_jobs import enqueue_agent_terminal_job

        slow = enqueue_agent_terminal_job(
            workspace_id="workspace_axon_watch",
            command="sleep 0.4; printf 'slow-done\\n'; exit 0",
            run_id="run_concurrent_jobs",
        )
        fast = enqueue_agent_terminal_job(
            workspace_id="workspace_axon_watch",
            command="printf 'fast-done\\n'; exit 7",
            run_id="run_concurrent_jobs",
        )

        slow_record = self._await_terminal_status(str(slow["job_id"]))
        fast_record = self._await_terminal_status(str(fast["job_id"]))
        self.assertEqual(0, slow_record.get("exit_code"))
        self.assertEqual("completed", slow_record.get("status"))
        self.assertEqual(7, fast_record.get("exit_code"))
        self.assertEqual("failed", fast_record.get("status"))

    def test_hung_job_is_interrupted_at_its_own_deadline(self) -> None:
        from app.terminal.agent_jobs import enqueue_agent_terminal_job

        job = enqueue_agent_terminal_job(
            workspace_id="workspace_axon_watch",
            command="sleep 600",
            run_id="run_hung_job",
            timeout_seconds=1,
        )
        self.assertEqual(1, job.get("timeout_seconds"))

        record = self._await_terminal_status(str(job["job_id"]))
        self.assertEqual("timed_out", record.get("status"))
        self.assertIn("deadline", str(record.get("failure_reason") or ""))

    def test_cancel_closes_out_a_running_job(self) -> None:
        from app.terminal.agent_jobs import cancel_agent_terminal_job, enqueue_agent_terminal_job

        job = enqueue_agent_terminal_job(
            workspace_id="workspace_axon_watch",
            command="sleep 600",
            run_id="run_cancel_job",
        )
        cancelled = cancel_agent_terminal_job(str(job["job_id"]))
        self.assertIsNotNone(cancelled)
        assert cancelled is not None
        self.assertEqual("cancelled", cancelled.get("status"))
        self.assertIn("cancelled by operator", str(cancelled.get("failure_reason") or ""))

    def test_ship_jobs_get_a_longer_default_deadline(self) -> None:
        """OTA/Vercel ship jobs must not inherit the short worker deadline."""
        from app.terminal.agent_job_watcher import (
            DEFAULT_JOB_TIMEOUT_SECONDS,
            SHIP_JOB_TIMEOUT_SECONDS,
            resolve_timeout_seconds,
        )

        self.assertEqual(
            SHIP_JOB_TIMEOUT_SECONDS,
            resolve_timeout_seconds(None, command="npm run ota:canary"),
        )
        self.assertEqual(
            DEFAULT_JOB_TIMEOUT_SECONDS,
            resolve_timeout_seconds(None, command="npm test -- tests/foo.test.ts"),
        )
        # An explicit override still wins, capped at the ceiling.
        self.assertEqual(30.0, resolve_timeout_seconds(30, command="npm run ota:canary"))

    def test_cancel_unknown_job_returns_none(self) -> None:
        from app.terminal.agent_jobs import cancel_agent_terminal_job

        self.assertIsNone(cancel_agent_terminal_job("agent-job-missing"))

    def test_stale_active_stream_target_does_not_block_job_enqueue(self) -> None:
        from app.terminal.active_chat_stream import register_active_chat_stream
        from app.terminal.agent_jobs import enqueue_agent_terminal_job

        register_active_chat_stream(
            workspace_id="workspace_axon_watch",
            thread_id="thread_missing",
            message_id="message_missing",
            run_id="run_stale_stream",
        )

        job = enqueue_agent_terminal_job(
            workspace_id="workspace_axon_watch",
            command="echo no-stream-target-ok",
            run_id="run_stale_stream",
            stream_to_chat=True,
        )

        self.assertEqual("running", job["status"])
        self.assertFalse(job.get("stream_to_chat"))
        self.assertIsNone(job.get("thread_id"))
        self.assertIsNone(job.get("message_id"))


if __name__ == "__main__":
    unittest.main()
