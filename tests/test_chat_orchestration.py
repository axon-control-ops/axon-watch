from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.chat.orchestration import (  # noqa: E402
    build_agent_command_reply,
    orchestrate_command_run,
)


class ChatOrchestrationTests(unittest.TestCase):
    def test_build_agent_reply_for_dispatch_includes_summary(self) -> None:
        content = build_agent_command_reply(
            content="inspect runtime",
            run_record={
                "run_id": "run_test",
                "phase": "executing",
                "summary": "inspect runtime",
            },
            dispatched=True,
        )
        self.assertIn("run_test", content)
        self.assertIn("inspect runtime", content)

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
        self.assertIs(
            orchestrate_command_run(run_record=record, dispatched=False),
            record,
        )


if __name__ == "__main__":
    unittest.main()
