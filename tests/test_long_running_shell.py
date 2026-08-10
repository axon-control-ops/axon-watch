"""Tests for long-running ship shell classifier and axon job terminal fences."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.cli_runtime.long_running_shell import is_long_running_ship_shell  # noqa: E402
from app.cli_runtime.long_running_shell_prompt import LONG_RUNNING_SHELL_CLAUSE  # noqa: E402
from app.cli_runtime.stream_blocks.terminal_blocks import (  # noqa: E402
    render_axon_job_terminal_fence,
    upsert_axon_job_terminal_fence,
)
from app.terminal.agent_job_chat import (  # noqa: E402
    append_live_job_fence_body,
    close_live_job_fence,
    merge_active_agent_job_terminals,
    register_live_job_fence,
    reset_live_job_fences,
)


class LongRunningShellTests(unittest.TestCase):
    def test_prompt_clause_does_not_block_on_disposable_git(self) -> None:
        self.assertIn("missing `.git`", LONG_RUNNING_SHELL_CLAUSE)
        self.assertIn("real workspace by `--workspace`", LONG_RUNNING_SHELL_CLAUSE)
        self.assertIn("`--no-stream`", LONG_RUNNING_SHELL_CLAUSE)

    def test_classifier_matches_ota_eas_expo(self) -> None:
        self.assertTrue(is_long_running_ship_shell("npm run ota:canary"))
        self.assertTrue(is_long_running_ship_shell("eas update --branch operator-canary"))
        self.assertTrue(is_long_running_ship_shell("npx expo export --platform android"))
        self.assertFalse(is_long_running_ship_shell("git status"))
        self.assertFalse(is_long_running_ship_shell("npm test"))
        self.assertFalse(is_long_running_ship_shell("npm run export"))

    def test_render_and_upsert_open_then_close_fence(self) -> None:
        open_fence = render_axon_job_terminal_fence(
            command="npm run ota:canary",
            job_id="agent-job-abc",
            body="bundling…\n",
            closed=False,
        )
        self.assertIn(":::terminal npm run ota:canary", open_fence)
        self.assertIn("# axon-job:agent-job-abc", open_fence)
        self.assertIn("bundling…", open_fence)
        self.assertFalse(open_fence.rstrip().endswith(":::"))

        content = "Earlier assistant text.\n"
        content = upsert_axon_job_terminal_fence(content, open_fence, job_id="agent-job-abc")
        self.assertIn("Earlier assistant text.", content)
        self.assertIn("bundling…", content)

        grown = render_axon_job_terminal_fence(
            command="npm run ota:canary",
            job_id="agent-job-abc",
            body="bundling…\n98%\n",
            closed=False,
        )
        content = upsert_axon_job_terminal_fence(content, grown, job_id="agent-job-abc")
        self.assertIn("98%", content)
        self.assertEqual(content.count("# axon-job:agent-job-abc"), 1)

        closed = render_axon_job_terminal_fence(
            command="npm run ota:canary",
            job_id="agent-job-abc",
            body="bundling…\n98%\ndone\n",
            closed=True,
            exit_code=0,
        )
        content = upsert_axon_job_terminal_fence(content, closed, job_id="agent-job-abc")
        self.assertIn("[exit 0]", content)
        self.assertTrue(":::" in content.split("# axon-job:agent-job-abc", 1)[1])

    def test_merge_preserves_fence_when_assembler_overwrites(self) -> None:
        reset_live_job_fences()
        self.addCleanup(reset_live_job_fences)
        register_live_job_fence(
            job_id="agent-job-1",
            message_id="message_agent_1",
            command="npm run ota:canary",
        )
        append_live_job_fence_body("agent-job-1", "message_agent_1", "expo 50%\n")
        assembler = "Thinking about next steps.\n"
        merged = merge_active_agent_job_terminals("message_agent_1", assembler)
        self.assertIn("Thinking about next steps.", merged)
        self.assertIn("expo 50%", merged)
        self.assertIn("# axon-job:agent-job-1", merged)
        close_live_job_fence("agent-job-1", "message_agent_1", exit_code=0)
        closed = merge_active_agent_job_terminals("message_agent_1", assembler)
        self.assertIn("[exit 0]", closed)


if __name__ == "__main__":
    unittest.main()
