from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.chat.command_executor import CommandExecutionResult  # noqa: E402
from app.chat.orchestration import (  # noqa: E402
    build_agent_command_reply,
    orchestrate_command_run,
)
from app.persistence import run_store  # noqa: E402
from app.runs.service import RunLifecycleError, create_run  # noqa: E402
from tests.support.control_plane_db import isolate_control_plane_db  # noqa: E402


class ChatOrchestrationTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)

    def test_build_agent_reply_includes_execution_evidence(self) -> None:
        execution = CommandExecutionResult(
            intent="health_probe",
            success=True,
            output='{"status":"ok"}',
            receipt_summary="Health probe succeeded",
        )
        content = build_agent_command_reply(
            content="check health",
            run_record={
                "run_id": "run_test",
                "phase": "completed",
                "summary": "check health",
            },
            dispatched=True,
            execution=execution,
        )
        self.assertIn("Executed `health_probe`", content)
        self.assertIn('{"status":"ok"}', content)
        self.assertIn("completed", content)
        self.assertNotIn("Review when ready.", content)

    def test_build_agent_reply_omits_review_prompt_when_completed(self) -> None:
        execution = CommandExecutionResult(
            intent="git_status",
            success=True,
            output="On branch dev",
            receipt_summary="Git status succeeded",
        )
        content = build_agent_command_reply(
            content="git status",
            run_record={
                "run_id": "run_test",
                "phase": "completed",
                "summary": "Git status",
            },
            dispatched=True,
            execution=execution,
        )
        self.assertIn("Phase is now completed", content)
        self.assertNotIn("Review when ready.", content)

    def test_orchestrate_auto_completes_read_only_intents(self) -> None:
        execution = CommandExecutionResult(
            intent="git_status",
            success=True,
            output="On branch dev",
            receipt_summary="Git status succeeded",
        )
        with patch("app.chat.orchestration.execute_command", return_value=execution), patch(
            "app.chat.orchestration.append_run_execution_receipt",
            return_value={"run_id": "run_test", "phase": "executing", "summary": "Git status"},
        ) as append_mock, patch(
            "app.chat.orchestration.complete_run",
            return_value={"run_id": "run_test", "phase": "completed", "summary": "Git status"},
        ) as complete_mock, patch(
            "app.chat.orchestration.mark_review_ready",
        ) as review_mock:
            record, exec_result = orchestrate_command_run(
                workspace_id="workspace_alpha",
                content="git status",
                run_record={"run_id": "run_test", "phase": "executing", "summary": "Git status"},
                dispatched=True,
            )
            append_mock.assert_called_once()
            complete_mock.assert_called_once_with("run_test")
            review_mock.assert_not_called()
            self.assertEqual(record["phase"], "completed")
            self.assertIs(exec_result, execution)

    def test_orchestrate_auto_completes_reversible_shell_check_health(self) -> None:
        execution = CommandExecutionResult(
            intent="shell_command",
            success=True,
            output="ok",
            receipt_summary="check-health succeeded",
        )
        with patch("app.chat.orchestration.execute_command", return_value=execution), patch(
            "app.chat.orchestration.append_run_execution_receipt",
            return_value={
                "run_id": "run_health",
                "phase": "executing",
                "summary": "check-health",
            },
        ), patch(
            "app.chat.orchestration.complete_run",
            return_value={
                "run_id": "run_health",
                "phase": "completed",
                "summary": "check-health",
            },
        ) as complete_mock, patch(
            "app.chat.orchestration.mark_review_ready",
        ) as review_mock:
            record, _exec = orchestrate_command_run(
                workspace_id="workspace_alpha",
                content="check health",
                run_record={
                    "run_id": "run_health",
                    "phase": "executing",
                    "summary": "check-health",
                },
                dispatched=True,
            )
            complete_mock.assert_called_once_with("run_health")
            review_mock.assert_not_called()
            self.assertEqual(record["phase"], "completed")

    def test_orchestrate_finalization_error_fails_run(self) -> None:
        execution = CommandExecutionResult(
            intent="health_probe",
            success=True,
            output="ok",
            receipt_summary="health ok",
        )
        with patch("app.chat.orchestration.execute_command", return_value=execution), patch(
            "app.chat.orchestration.append_run_execution_receipt",
            return_value={"run_id": "run_stuck", "phase": "executing", "summary": "health"},
        ), patch(
            "app.chat.orchestration.complete_run",
            side_effect=RunLifecycleError("complete blocked"),
        ), patch(
            "app.chat.orchestration.fail_run",
            return_value={"run_id": "run_stuck", "phase": "failed", "summary": "health"},
        ) as fail_mock:
            record, _exec = orchestrate_command_run(
                workspace_id="workspace_alpha",
                content="health",
                run_record={"run_id": "run_stuck", "phase": "executing", "summary": "health"},
                dispatched=True,
            )
            fail_mock.assert_called_once()
            self.assertEqual(record["phase"], "failed")

    def test_runtime_finalization_failure_persists_failed_receipt(self) -> None:
        created = create_run(
            workspace_id="workspace_alpha",
            mode="agent",
            summary="health",
        )
        execution = CommandExecutionResult(
            intent="health_probe",
            success=True,
            output="ok",
            receipt_summary="Health probe succeeded",
        )
        with patch("app.chat.orchestration.execute_command", return_value=execution), patch(
            "app.chat.orchestration.complete_run",
            side_effect=RunLifecycleError("complete blocked"),
        ):
            record, _exec = orchestrate_command_run(
                workspace_id="workspace_alpha",
                content="health",
                run_record=created,
                dispatched=True,
            )

        self.assertEqual("failed", record["phase"])
        history = run_store.list_history(str(record["history_ref"]))
        receipt = history[-1]["receipt"]
        self.assertEqual("run_failed", receipt["type"])
        self.assertIn("Run finalization failed: complete blocked", receipt["summary"])

    def test_runtime_double_finalization_failure_persists_error_receipt(self) -> None:
        created = create_run(
            workspace_id="workspace_alpha",
            mode="agent",
            summary="health",
        )
        execution = CommandExecutionResult(
            intent="health_probe",
            success=True,
            output="ok",
            receipt_summary="Health probe succeeded",
        )
        with patch("app.chat.orchestration.execute_command", return_value=execution), patch(
            "app.chat.orchestration.complete_run",
            side_effect=RunLifecycleError("complete blocked"),
        ), patch(
            "app.chat.orchestration.fail_run",
            side_effect=RunLifecycleError("fail blocked"),
        ):
            record, _exec = orchestrate_command_run(
                workspace_id="workspace_alpha",
                content="health",
                run_record=created,
                dispatched=True,
            )

        self.assertEqual("executing", record["phase"])
        history = run_store.list_history(str(record["history_ref"]))
        receipt = history[-1]["receipt"]
        self.assertEqual("finalization_error", receipt["type"])
        self.assertIn("complete blocked", receipt["summary"])
        self.assertIn("success=False", receipt["summary"])

    def test_build_agent_reply_for_attach_notes_active_run(self) -> None:
        content = build_agent_command_reply(
            content="add context",
            run_record={"run_id": "run_active", "phase": "executing", "summary": "Active"},
            dispatched=False,
        )
        self.assertIn("linked to active run", content)
        self.assertIn("run_active", content)

    def test_orchestrate_command_run_noops_when_not_dispatched(self) -> None:
        record = {"run_id": "run_active", "phase": "executing", "summary": "Active"}
        result_record, execution = orchestrate_command_run(
            workspace_id="workspace_alpha",
            content="list files",
            run_record=record,
            dispatched=False,
        )
        self.assertIs(result_record, record)
        self.assertIsNone(execution)

    def test_build_agent_reply_for_resume_from_review_omits_review_prompt(self) -> None:
        execution = CommandExecutionResult(
            intent="resume_from_review",
            success=True,
            output="Resumed run_test from review_ready to executing.",
            receipt_summary="Resumed run run_test from review_ready",
            run_id="run_test",
        )
        content = build_agent_command_reply(
            content="resume from review",
            run_record={"run_id": "run_test", "phase": "executing", "summary": "Follow-up"},
            dispatched=False,
            execution=execution,
        )
        self.assertIn("resume_from_review", content)
        self.assertNotIn("Review when ready.", content)


if __name__ == "__main__":
    unittest.main()
