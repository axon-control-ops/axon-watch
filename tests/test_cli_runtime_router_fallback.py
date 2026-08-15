"""CLI router fallback messaging and Cursor recursion recovery."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.cli_runtime.cursor_agent import (  # noqa: E402
    CursorAgentReply,
    is_recursion_depth_error,
)
from app.cli_runtime.router import _fallback_reply, dispatch_ide_composer  # noqa: E402


def _snapshot_cursor_and_codex_ready() -> dict[str, object]:
    """Both candidates ready — needed to exercise the fallback-through-multiple
    runtimes path (a single-ready-candidate fixture can't distinguish "first
    attempted" from "last attempted", since they're the same candidate)."""
    return {
        "default_runtime": "cursor_local",
        "local": [
            {
                "id": "cursor_local",
                "family": "cursor",
                "label": "Cursor CLI (local)",
                "binary": "cursor",
                "ready": True,
                "available": True,
                "target_type": "local",
                "auth": {"logged_in": True},
            },
            {
                "id": "codex_local",
                "family": "codex",
                "label": "Codex CLI (local)",
                "binary": "codex",
                "ready": True,
                "available": True,
                "target_type": "local",
                "auth": {"logged_in": True},
            },
        ],
        "cloud": [],
    }


def _snapshot_cursor_ready() -> dict[str, object]:
    return {
        "default_runtime": "cursor_local",
        "local": [
            {
                "id": "cursor_local",
                "family": "cursor",
                "label": "Cursor CLI (local)",
                "binary": "cursor",
                "ready": True,
                "available": True,
                "target_type": "local",
                "auth": {"logged_in": True},
            },
            {
                "id": "codex_local",
                "family": "codex",
                "label": "Codex CLI (local)",
                "binary": "codex",
                "ready": False,
                "available": False,
                "target_type": "local",
                "auth": {},
            },
        ],
        "cloud": [
            {
                "id": "cursor_cloud",
                "family": "cursor",
                "label": "Cursor Cloud Agent",
                "ready": False,
                "available": False,
                "target_type": "cloud",
                "auth": {},
            },
            {
                "id": "codex_cloud",
                "family": "codex",
                "label": "Codex Cloud Task",
                "ready": False,
                "available": False,
                "target_type": "cloud",
                "auth": {},
            },
        ],
    }


class RecursionDepthHelperTests(unittest.TestCase):
    def test_detects_python_recursion_message(self) -> None:
        self.assertTrue(is_recursion_depth_error("maximum recursion depth exceeded"))
        self.assertTrue(
            is_recursion_depth_error("RuntimeError: maximum recursion depth exceeded while calling")
        )
        self.assertFalse(is_recursion_depth_error("Cursor auth probe timed out"))


class FallbackReplyTests(unittest.TestCase):
    def test_not_ready_copy_preserved(self) -> None:
        reply = _fallback_reply(
            composer_mode="ask",
            user_prompt="status",
            context_block="ctx",
            reason="Cursor auth probe timed out",
        )
        self.assertIn("no CLI runtime is ready", reply)
        self.assertNotIn("failed on", reply)
        self.assertIn("cursor agent status", reply.lower())
        self.assertNotIn("Open Runtime or `/vault`", reply)

    def test_run_error_copy_distinguishes_ready_crash(self) -> None:
        reply = _fallback_reply(
            composer_mode="ask",
            user_prompt="status",
            context_block="ctx",
            reason="maximum recursion depth exceeded",
            failure_phase="run_error",
            runtime_label="Cursor CLI (local)",
        )
        self.assertIn("failed on Cursor CLI (local)", reply)
        self.assertIn("maximum recursion depth exceeded", reply)
        self.assertNotIn("no CLI runtime is ready", reply)
        self.assertNotIn("Open Runtime or `/vault`", reply)

    def test_usage_limit_run_error_does_not_blame_vault(self) -> None:
        reply = _fallback_reply(
            composer_mode="agent",
            user_prompt="continue",
            context_block="ctx",
            reason="ActionRequiredError: You've hit your usage limit",
            failure_phase="run_error",
            runtime_label="Cursor CLI (local)",
        )
        self.assertIn("could not start", reply.lower())
        self.assertIn("usage", reply.lower())
        self.assertNotIn("/vault", reply.lower())
        self.assertIn("Check Cursor Usage", reply)

    def test_unpaid_invoice_run_error_points_to_dashboard(self) -> None:
        reply = _fallback_reply(
            composer_mode="agent",
            user_prompt="continue",
            context_block="ctx",
            reason=(
                "ActionRequiredError: You have an unpaid invoice Visit "
                "cursor.com/dashboard and pay your invoice in Stripe to resume requests."
            ),
            failure_phase="run_error",
            runtime_label="Cursor CLI (local)",
        )
        self.assertIn("could not start", reply.lower())
        self.assertIn("unpaid invoice", reply.lower())
        self.assertIn("cursor.com/dashboard", reply.lower())
        self.assertNotIn("/vault", reply.lower())
        self.assertNotIn("Check Cursor Usage", reply)


class DispatchRecursionRecoveryTests(unittest.TestCase):
    def test_recursion_retries_once_without_research_mcp(self) -> None:
        calls: list[bool | None] = []

        def fake_run_cursor_local(**kwargs):  # noqa: ANN003
            research = kwargs.get("research_available")
            calls.append(research)
            if research is None:
                raise RuntimeError("maximum recursion depth exceeded")
            self.assertIs(research, False)
            return CursorAgentReply(content="Recovered without research MCP.")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with (
                patch(
                    "app.cli_runtime.router.runtime_status_snapshot",
                    return_value=_snapshot_cursor_ready(),
                ),
                patch(
                    "app.cli_runtime.router._resolve_workspace_root",
                    return_value=root,
                ),
                patch(
                    "app.cli_runtime.router.ensure_workspace_research_mcp",
                    return_value=True,
                ),
                patch(
                    "app.cli_runtime.cursor_agent.run_cursor_local",
                    side_effect=fake_run_cursor_local,
                ),
            ):
                result = dispatch_ide_composer(
                    workspace_id="workspace_dashpro",
                    composer_mode="ask",
                    user_prompt="What about DashPro errors and OTA?",
                    context_block="ctx",
                    runtime_target="cursor_local",
                )

        self.assertTrue(result.get("dispatched"))
        self.assertEqual("Recovered without research MCP.", result.get("content"))
        self.assertEqual([None, False], calls)

    def test_recursion_then_repeat_uses_run_error_message(self) -> None:
        def always_recurse(**_kwargs):  # noqa: ANN003
            raise RuntimeError("maximum recursion depth exceeded")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with (
                patch(
                    "app.cli_runtime.router.runtime_status_snapshot",
                    return_value=_snapshot_cursor_ready(),
                ),
                patch(
                    "app.cli_runtime.router._resolve_workspace_root",
                    return_value=root,
                ),
                patch(
                    "app.cli_runtime.router.ensure_workspace_research_mcp",
                    return_value=True,
                ),
                patch(
                    "app.cli_runtime.cursor_agent.run_cursor_local",
                    side_effect=always_recurse,
                ),
            ):
                result = dispatch_ide_composer(
                    workspace_id="workspace_dashpro",
                    composer_mode="ask",
                    user_prompt="What about DashPro errors and OTA?",
                    context_block="ctx",
                    runtime_target="cursor_local",
                )

        self.assertFalse(result.get("dispatched"))
        self.assertEqual("run_error", result.get("failure_phase"))
        content = str(result.get("content") or "")
        self.assertIn("failed on Cursor CLI (local)", content)
        self.assertIn("maximum recursion depth exceeded", content)
        self.assertNotIn("no CLI runtime is ready", content)
        reason = str(result.get("reason") or "")
        self.assertIn("maximum recursion depth exceeded", reason)
        self.assertNotIn("Codex CLI (local) unavailable", reason)

    def test_explicit_runtime_never_falls_through_to_another_provider(self) -> None:
        # Regression: an operator with Cursor explicitly selected must never
        # silently consume Codex capacity after Cursor fails. Fallback is only
        # valid for Auto (no runtime_target) dispatch.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with (
                patch(
                    "app.cli_runtime.router.runtime_status_snapshot",
                    return_value=_snapshot_cursor_and_codex_ready(),
                ),
                patch(
                    "app.cli_runtime.router._resolve_workspace_root",
                    return_value=root,
                ),
                patch(
                    "app.cli_runtime.router.ensure_workspace_research_mcp",
                    return_value=True,
                ),
                patch(
                    "app.cli_runtime.cursor_agent.run_cursor_local",
                    side_effect=RuntimeError("Cursor is installed but not signed in."),
                ),
                patch(
                    "app.cli_runtime.router.run_non_cursor_local",
                    side_effect=RuntimeError("Codex/OpenAI API key was rejected."),
                ) as mock_non_cursor,
            ):
                result = dispatch_ide_composer(
                    workspace_id="workspace_dashpro",
                    composer_mode="ask",
                    user_prompt="What about DashPro errors and OTA?",
                    context_block="ctx",
                    runtime_target="cursor_local",
                )

        self.assertFalse(result.get("dispatched"))
        content = str(result.get("content") or "")
        self.assertIn("failed on Cursor CLI (local)", content)
        self.assertNotIn("failed on Codex CLI (local)", content)
        reason = str(result.get("reason") or "")
        self.assertIn("not signed in", reason)
        self.assertNotIn("API key was rejected", reason)
        mock_non_cursor.assert_not_called()

    def test_autonomous_worker_uses_only_approved_fallback_family(self) -> None:
        snapshot = _snapshot_cursor_and_codex_ready()
        snapshot["codex_usage"] = {"limit_reached": True}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with (
                patch("app.cli_runtime.router.runtime_status_snapshot", return_value=snapshot),
                patch("app.cli_runtime.router._resolve_workspace_root", return_value=root),
                patch("app.cli_runtime.router.ensure_workspace_research_mcp", return_value=True),
                patch(
                    "app.cli_runtime.router.run_cursor_local_with_recursion_retry",
                    return_value=CursorAgentReply(content="Recovered on approved Cursor fallback."),
                ) as mock_cursor,
                patch("app.cli_runtime.router.run_non_cursor_local") as mock_non_cursor,
            ):
                result = dispatch_ide_composer(
                    workspace_id="workspace_young_eagles_day_care",
                    composer_mode="agent",
                    user_prompt="Continue the bounded task.",
                    context_block="ctx",
                    runtime_target="codex_local",
                    fallback_runtime_families=("cursor",),
                )

        self.assertTrue(result.get("dispatched"))
        self.assertEqual("cursor_local", result.get("runtime_id"))
        self.assertTrue(
            str(result.get("content") or "").startswith("Recovered on approved Cursor fallback.")
        )
        mock_cursor.assert_called_once()
        mock_non_cursor.assert_not_called()

    def test_revoked_claude_oauth_retries_configured_vault_key(self) -> None:
        snapshot = {
            "default_runtime": "claude_local",
            "local": [
                {
                    "id": "claude_local",
                    "family": "claude",
                    "label": "Claude",
                    "binary": "claude",
                    "ready": True,
                    "available": True,
                    "target_type": "local",
                    "auth": {"logged_in": True, "auth_method": "oauth"},
                }
            ],
            "cloud": [],
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with (
                patch("app.cli_runtime.router.runtime_status_snapshot", return_value=snapshot),
                patch("app.cli_runtime.router._resolve_workspace_root", return_value=root),
                patch("app.cli_runtime.router.ensure_workspace_research_mcp", return_value=True),
                patch(
                    "app.cli_runtime.router.runtime_subprocess_env",
                    return_value={"ANTHROPIC_API_KEY": "vault-key", "PATH": "/usr/bin"},
                ),
                patch(
                    "app.cli_runtime.router.run_non_cursor_local",
                    side_effect=[
                        RuntimeError("Failed to authenticate. API Error: 401 OAuth access token has been revoked."),
                        "Recovered with the configured provider key.",
                    ],
                ) as mock_non_cursor,
            ):
                result = dispatch_ide_composer(
                    workspace_id="workspace_young_eagles_day_care",
                    composer_mode="agent",
                    user_prompt="Continue the bounded task.",
                    context_block="ctx",
                    runtime_target="claude_local",
                    fallback_runtime_families=("claude",),
                )

        self.assertTrue(result.get("dispatched"))
        self.assertEqual("Recovered with the configured provider key.", result.get("content"))
        self.assertNotIn("ANTHROPIC_API_KEY", mock_non_cursor.call_args_list[0].kwargs["subprocess_env"])
        self.assertEqual(
            "vault-key",
            mock_non_cursor.call_args_list[1].kwargs["subprocess_env"]["ANTHROPIC_API_KEY"],
        )

    def test_explicit_codex_quota_does_not_replace_signed_in_account_with_vault_key(self) -> None:
        snapshot = {
            "default_runtime": "codex_local",
            "local": [
                {
                    "id": "codex_local",
                    "family": "codex",
                    "label": "Codex CLI",
                    "binary": "codex",
                    "ready": True,
                    "available": True,
                    "target_type": "local",
                    "auth": {"logged_in": True, "auth_method": "chatgpt"},
                }
            ],
            "cloud": [],
            "codex_usage": {"limit_reached": True},
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with (
                patch("app.cli_runtime.router.runtime_status_snapshot", return_value=snapshot),
                patch("app.cli_runtime.router._resolve_workspace_root", return_value=root),
                patch("app.cli_runtime.router.ensure_workspace_research_mcp", return_value=True),
                patch(
                    "app.cli_runtime.router.runtime_subprocess_env",
                    return_value={"OPENAI_API_KEY": "stale-vault-key", "PATH": "/usr/bin"},
                ),
                patch("app.cli_runtime.router.run_non_cursor_local") as run_codex,
            ):
                result = dispatch_ide_composer(
                    workspace_id="workspace_young_eagles_day_care",
                    composer_mode="agent",
                    user_prompt="Continue the bounded task.",
                    context_block="ctx",
                    runtime_target="codex_local",
                )

        self.assertFalse(result.get("dispatched"))
        self.assertIn("usage limit is still active", str(result.get("reason") or ""))
        run_codex.assert_not_called()

    def test_codex_subscription_limit_retries_configured_vault_key(self) -> None:
        snapshot = {
            "default_runtime": "codex_local",
            "local": [
                {
                    "id": "codex_local",
                    "family": "codex",
                    "label": "Codex",
                    "binary": "codex",
                    "ready": True,
                    "available": True,
                    "target_type": "local",
                    "auth": {"logged_in": True, "auth_method": "chatgpt"},
                }
            ],
            "cloud": [],
            "codex_usage": {"limit_reached": False},
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with (
                patch("app.cli_runtime.router.runtime_status_snapshot", return_value=snapshot),
                patch("app.cli_runtime.router._resolve_workspace_root", return_value=root),
                patch("app.cli_runtime.router.ensure_workspace_research_mcp", return_value=True),
                patch(
                    "app.cli_runtime.router.runtime_subprocess_env",
                    return_value={
                        "OPENAI_API_KEY": "vault-key",
                        "AXON_WATCH_RUNTIME_PROFILE_ROOT": tmp,
                        "PATH": "/usr/bin",
                    },
                ),
                patch(
                    "app.cli_runtime.router.default_codex_model",
                    return_value="gpt-test",
                ),
                patch(
                    "app.cli_runtime.router.run_non_cursor_local",
                    side_effect=[
                        RuntimeError("You've hit your usage limit"),
                        "Recovered with the configured OpenAI key.",
                    ],
                ) as mock_non_cursor,
            ):
                result = dispatch_ide_composer(
                    workspace_id="workspace_young_eagles_day_care",
                    composer_mode="agent",
                    user_prompt="Continue the bounded task.",
                    context_block="ctx",
                    runtime_target="codex_local",
                    fallback_runtime_families=("codex",),
                )

        self.assertTrue(result.get("dispatched"))
        self.assertEqual("Recovered with the configured OpenAI key.", result.get("content"))
        self.assertNotIn("OPENAI_API_KEY", mock_non_cursor.call_args_list[0].kwargs["subprocess_env"])
        self.assertEqual(
            "vault-key",
            mock_non_cursor.call_args_list[1].kwargs["subprocess_env"]["OPENAI_API_KEY"],
        )


if __name__ == "__main__":
    unittest.main()
