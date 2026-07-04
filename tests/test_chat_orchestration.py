from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.chat.command_executor import CommandExecutionResult  # noqa: E402
from app.chat.orchestration import (  # noqa: E402
    build_agent_command_reply,
    orchestrate_command_run,
)


class ChatOrchestrationTests(unittest.TestCase):
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
                "phase": "review_ready",
                "summary": "check health",
            },
            dispatched=True,
            execution=execution,
        )
        self.assertIn("Executed `health_probe`", content)
        self.assertIn('{"status":"ok"}', content)
        self.assertIn("review_ready", content)

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


if __name__ == "__main__":
    unittest.main()
