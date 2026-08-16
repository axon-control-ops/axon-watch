from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.cli_runtime.codex_agent import _build_codex_exec_command, _extract_codex_text, run_codex_local  # noqa: E402
from app.cli_runtime.claude_agent import _extract_claude_text, run_claude_local  # noqa: E402
from app.cli_runtime.cursor_agent import CursorAgentReply, _cursor_mode_flag, run_cursor_local  # noqa: E402


def _stream_json_stdout(text: str) -> str:
    return (
        '{"type":"system","subtype":"init","session_id":"s1"}\n'
        '{"type":"assistant","message":{"role":"assistant","content":'
        '[{"type":"text","text":"' + text + '"}]},"session_id":"s1"}\n'
        '{"type":"result","subtype":"success","is_error":false,"result":"' + text + '"}\n'
    )


class CliRuntimeAgentTests(unittest.TestCase):
    def test_cursor_mode_flag_never_passes_agent(self) -> None:
        self.assertEqual("ask", _cursor_mode_flag("ask", "consultative"))
        self.assertEqual("plan", _cursor_mode_flag("plan", "executing"))
        self.assertEqual("plan", _cursor_mode_flag("agent", "consultative"))
        self.assertEqual("plan", _cursor_mode_flag("debug", "consultative"))
        # Cursor CLI rejects --mode agent; full access omits the flag entirely.
        self.assertEqual("", _cursor_mode_flag("agent", "executing"))
        self.assertEqual("", _cursor_mode_flag("debug", "executing"))

    @patch("app.cli_runtime.cursor_agent.communicate_registered_process")
    def test_cursor_parses_stream_json_reply(self, mock_communicate) -> None:
        mock_communicate.return_value = (_stream_json_stdout("PONG"), "", 0)
        reply = run_cursor_local(
            binary="/usr/bin/cursor",
            prompt="ping",
            workspace_root=Path("/tmp"),
            composer_mode="agent",
        )
        self.assertEqual("PONG", reply.content)
        command = mock_communicate.call_args.kwargs["command"]
        self.assertIn("stream-json", command)
        self.assertIn("plan", command)

    @patch("app.cli_runtime.cursor_agent.stream_registered_process")
    def test_cursor_streams_assistant_deltas_not_raw_json(self, mock_stream) -> None:
        raw = _stream_json_stdout("Hello world")

        def fake_stream(*, run_id, command, timeout_seconds, subprocess_env, on_chunk, cwd=None):
            accumulated = ""
            for line in raw.splitlines(keepends=True):
                accumulated += line
                on_chunk(accumulated, line)
            return raw, "", 0

        mock_stream.side_effect = fake_stream
        chunks: list[str] = []
        reply = run_cursor_local(
            binary="/usr/bin/cursor",
            prompt="ping",
            workspace_root=Path("/tmp"),
            composer_mode="agent",
            execution_tier="executing",
            on_chunk=lambda accumulated, delta: chunks.append(delta),
        )
        self.assertEqual("Hello world", reply.content)
        self.assertEqual(["Hello world"], chunks)
        command = mock_stream.call_args.kwargs["command"]
        self.assertNotIn("--mode", command)

    @patch("app.cli_runtime.cursor_agent.communicate_registered_process")
    @patch("app.cli_runtime.cursor_agent.research_capability_snapshot")
    def test_cursor_adds_force_and_approve_mcps_when_research_available(
        self,
        mock_research_snapshot,
        mock_communicate,
    ) -> None:
        mock_research_snapshot.return_value = {"available": True}
        mock_communicate.return_value = (_stream_json_stdout("PONG"), "", 0)
        run_cursor_local(
            binary="/usr/bin/cursor",
            prompt="ping",
            workspace_root=Path("/tmp"),
            composer_mode="agent",
        )
        command = mock_communicate.call_args.kwargs["command"]
        self.assertIn("--force", command)
        self.assertIn("--approve-mcps", command)

    @patch("app.cli_runtime.cursor_agent.communicate_registered_process")
    def test_cursor_assembles_thinking_and_edit_blocks(self, mock_communicate) -> None:
        stdout = (
            '{"type":"thinking","subtype":"delta","text":"Checking the file."}\n'
            '{"type":"thinking","subtype":"completed"}\n'
            '{"type":"tool_call","subtype":"completed","tool_call":{"editToolCall":'
            '{"args":{"path":"/tmp/ws/README.md"},"result":{"success":'
            '{"path":"/tmp/ws/README.md","linesAdded":1,"linesRemoved":0,'
            '"diffString":"--- a\\n+++ b\\n+<!-- hi -->"}}}}}\n'
            '{"type":"assistant","message":{"role":"assistant","content":'
            '[{"type":"text","text":"DONE"}]}}\n'
            '{"type":"result","subtype":"success","is_error":false,"result":"DONE"}\n'
        )
        mock_communicate.return_value = (stdout, "", 0)
        reply = run_cursor_local(
            binary="/usr/bin/cursor",
            prompt="edit it",
            workspace_root=Path("/tmp/ws"),
            composer_mode="agent",
            execution_tier="executing",
        )
        self.assertIn(":::thinking\nChecking the file.\n:::", reply.content)
        self.assertIn(":::edit README.md +1 -0", reply.content)
        self.assertIn("+<!-- hi -->", reply.content)
        self.assertTrue(reply.content.endswith("DONE"))

    @patch("app.cli_runtime.cursor_agent.communicate_registered_process")
    def test_cursor_error_result_raises(self, mock_communicate) -> None:
        mock_communicate.return_value = (
            '{"type":"result","subtype":"error","is_error":true,"result":"quota exceeded"}\n',
            "",
            0,
        )
        with self.assertRaisesRegex(RuntimeError, "quota exceeded"):
            run_cursor_local(
                binary="/usr/bin/cursor",
                prompt="ping",
                workspace_root=Path("/tmp"),
                composer_mode="ask",
            )

    @patch("app.cli_runtime.cursor_agent.communicate_registered_process")
    def test_cursor_timeout_is_normalized_to_runtime_error(self, mock_communicate) -> None:
        mock_communicate.side_effect = RuntimeError("CLI runtime timed out after 90s.")
        with self.assertRaisesRegex(RuntimeError, "CLI runtime timed out after 90s"):
            run_cursor_local(
                binary="/usr/bin/cursor",
                prompt="hello",
                workspace_root=Path("/tmp"),
                composer_mode="ask",
            )

    @patch("app.cli_runtime.codex_agent.communicate_registered_process")
    def test_codex_timeout_is_normalized_to_runtime_error(self, mock_communicate) -> None:
        mock_communicate.side_effect = RuntimeError("CLI runtime timed out after 90s.")
        with self.assertRaisesRegex(RuntimeError, "CLI runtime timed out after 90s"):
            run_codex_local(
                binary="/usr/bin/codex",
                prompt="hello",
                workspace_root=Path("/tmp"),
                composer_mode="ask",
            )

    def test_codex_uses_the_explicit_catalog_model(self) -> None:
        command = _build_codex_exec_command(
            binary="/usr/bin/codex",
            prompt="hello",
            workspace_root=Path("/tmp"),
            composer_mode="agent",
            model="gpt-5.5",
        )
        self.assertEqual("gpt-5.5", command[command.index("--model") + 1])

    def test_codex_uses_outer_sandbox_without_nested_workspace_write(self) -> None:
        command = _build_codex_exec_command(
            binary="/usr/bin/codex",
            prompt="ship canary",
            workspace_root=Path("/tmp/ws"),
            composer_mode="agent",
            execution_tier="executing",
            outer_sandboxed=True,
        )
        self.assertIn("danger-full-access", command)
        self.assertNotIn("workspace-write", command)
        self.assertIn('approval_policy="never"', command)

    def test_codex_passes_the_selected_reasoning_effort(self) -> None:
        command = _build_codex_exec_command(
            binary="/usr/bin/codex",
            prompt="hello",
            workspace_root=Path("/tmp"),
            composer_mode="agent",
            model="gpt-5.5",
            reasoning_effort="high",
        )
        self.assertIn('model_reasoning_effort="high"', command)

    def test_codex_preserves_command_and_file_change_blocks(self) -> None:
        stream = (
            '{"type":"item.completed","item":{"type":"command_execution",'
            '"command":"npm test","aggregated_output":"PASS", "exit_code":0}}\n'
            '{"type":"item.completed","item":{"type":"file_change","changes":['
            '{"path":"/tmp/ws/src/card.ts","diff":"--- a/src/card.ts\\n+++ b/src/card.ts\\n+new"}]}}\n'
            '{"type":"item.completed","item":{"type":"agent_message","text":"Done."}}\n'
        )
        transcript = _extract_codex_text(stream, Path("/tmp/ws"))
        self.assertIn(":::terminal npm test", transcript)
        self.assertIn("PASS", transcript)
        self.assertIn(":::edit src/card.ts +1 -0", transcript)
        self.assertIn("+new", transcript)
        self.assertTrue(transcript.endswith("Done."))

    def test_codex_shows_an_open_terminal_card_while_command_is_running(self) -> None:
        stream = (
            '{"type":"item.started","item":{"id":"cmd-1","type":"command_execution",'
            '"command":"npm test"}}\n'
        )
        transcript = _extract_codex_text(stream, Path("/tmp/ws"))
        self.assertIn(":::terminal npm test", transcript)
        self.assertIn("# Running…", transcript)

    def test_codex_preserves_structured_runtime_error_details(self) -> None:
        stream = (
            '{"type":"error","message":"401 Unauthorized: invalid API key"}\n'
            '{"type":"item.completed","item":{"type":"error",'
            '"message":"Falling back to HTTPS failed"}}\n'
        )
        transcript = _extract_codex_text(stream, Path("/tmp/ws"))
        self.assertIn(":::tool Error", transcript)
        self.assertIn("401 Unauthorized: invalid API key", transcript)
        self.assertIn("Falling back to HTTPS failed", transcript)

    @patch("app.cli_runtime.claude_agent.communicate_registered_process")
    def test_claude_parses_stream_json_reply(self, mock_communicate) -> None:
        mock_communicate.return_value = (_stream_json_stdout("PONG"), "", 0)
        reply = run_claude_local(
            binary="/usr/bin/claude",
            prompt="ping",
            workspace_root=Path("/tmp"),
            composer_mode="agent",
        )
        self.assertEqual("PONG", reply)
        command = mock_communicate.call_args.kwargs["command"]
        self.assertIn("-p", command)
        self.assertIn("stream-json", command)
        self.assertIn("plan", command)

    @patch("app.cli_runtime.claude_agent.communicate_registered_process")
    def test_claude_executing_uses_accept_edits(self, mock_communicate) -> None:
        mock_communicate.return_value = (_stream_json_stdout("DONE"), "", 0)
        run_claude_local(
            binary="/usr/bin/claude",
            prompt="edit",
            workspace_root=Path("/tmp/ws"),
            composer_mode="agent",
            execution_tier="executing",
        )
        command = mock_communicate.call_args.kwargs["command"]
        self.assertIn("acceptEdits", command)
        self.assertEqual("/tmp/ws", mock_communicate.call_args.kwargs.get("cwd"))

    def test_claude_preserves_tool_activity_as_terminal_and_edit_blocks(self) -> None:
        stream = "\n".join([
            json.dumps({"type": "assistant", "message": {"content": [
                {"type": "tool_use", "id": "bash-1", "name": "Bash", "input": {"command": "npm test"}},
                {"type": "tool_use", "id": "edit-1", "name": "Edit", "input": {"file_path": "/tmp/ws/src/card.ts", "old_string": "old", "new_string": "new"}},
            ]}}),
            json.dumps({"type": "user", "message": {"content": [
                {"type": "tool_result", "tool_use_id": "bash-1", "content": "PASS"},
            ]}}),
            json.dumps({"type": "result", "is_error": False, "result": "Done."}),
        ])
        transcript, error = _extract_claude_text(stream, Path("/tmp/ws"))
        self.assertEqual("", error)
        self.assertIn(":::terminal npm test", transcript)
        self.assertIn("PASS", transcript)
        self.assertIn(":::edit src/card.ts +1 -1", transcript)
        self.assertTrue(transcript.endswith("Done."))

    @patch("app.cli_runtime.claude_agent.communicate_registered_process")
    def test_claude_timeout_is_normalized_to_runtime_error(self, mock_communicate) -> None:
        mock_communicate.side_effect = RuntimeError("CLI runtime timed out after 90s.")
        with self.assertRaisesRegex(RuntimeError, "CLI runtime timed out after 90s"):
            run_claude_local(
                binary="/usr/bin/claude",
                prompt="hello",
                workspace_root=Path("/tmp"),
                composer_mode="ask",
            )


if __name__ == "__main__":
    unittest.main()
