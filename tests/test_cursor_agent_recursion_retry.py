"""Recursion-crash retry must actually remove the crashing MCP server.

Regression: run_cursor_local_with_recursion_retry retried with
research_available=False, which only skips *writing* a fresh
.cursor/mcp.json — the crashing server's entry from the first attempt was
still on disk, and Cursor CLI reads mcpServers from that file regardless of
any flag we pass per-invocation. The retry was therefore a no-op: it hit the
same recursion crash again and fell through to the next runtime candidate.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.cli_runtime.cursor_agent import (  # noqa: E402
    CursorAgentReply,
    run_cursor_local_with_recursion_retry,
)
from app.cli_runtime.research_mcp import ensure_workspace_research_mcp  # noqa: E402


class RecursionRetryMcpCleanupTests(unittest.TestCase):
    def test_retry_removes_stale_mcp_config_before_second_attempt(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            self.assertTrue(ensure_workspace_research_mcp(workspace_root))
            config_path = workspace_root / ".cursor" / "mcp.json"
            self.assertTrue(config_path.is_file())

            attempts: list[bool] = []

            def fake_run_cursor_local(*, research_available=None, **_kwargs):
                attempts.append(research_available)
                if len(attempts) == 1:
                    raise RuntimeError("maximum recursion depth exceeded")
                # Second attempt must see the config already gone from disk —
                # not just the (unused-by-Cursor-CLI) research_available flag.
                self.assertFalse(config_path.is_file())
                return CursorAgentReply(content="ok")

            with patch(
                "app.cli_runtime.cursor_agent.run_cursor_local",
                side_effect=fake_run_cursor_local,
            ):
                reply = run_cursor_local_with_recursion_retry(
                    runtime_id="cursor-agent",
                    workspace_id="workspace_demo",
                    binary="/usr/bin/cursor-agent",
                    prompt="hello",
                    workspace_root=workspace_root,
                    composer_mode="agent",
                    execution_tier="executing",
                    model="",
                    subprocess_env=None,
                    run_id="run_demo",
                    on_chunk=None,
                    trust_policy="operator",
                )

            self.assertEqual("ok", reply.content)
            self.assertEqual([None, False], attempts)
            self.assertFalse(config_path.is_file())

    def test_non_recursion_error_propagates_without_touching_mcp_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            self.assertTrue(ensure_workspace_research_mcp(workspace_root))
            config_path = workspace_root / ".cursor" / "mcp.json"

            with patch(
                "app.cli_runtime.cursor_agent.run_cursor_local",
                side_effect=RuntimeError("Could not install cursor-agent"),
            ):
                with self.assertRaises(RuntimeError):
                    run_cursor_local_with_recursion_retry(
                        runtime_id="cursor-agent",
                        workspace_id="workspace_demo",
                        binary="/usr/bin/cursor-agent",
                        prompt="hello",
                        workspace_root=workspace_root,
                        composer_mode="agent",
                        execution_tier="executing",
                        model="",
                        subprocess_env=None,
                        run_id="run_demo",
                        on_chunk=None,
                        trust_policy="operator",
                    )

            self.assertTrue(config_path.is_file())
            payload = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertIn("axon-research", payload["mcpServers"])


if __name__ == "__main__":
    unittest.main()
