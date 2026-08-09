from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.chat.lane_b_git_dispatch import (  # noqa: E402
    split_commit_then_remainder,
    try_lane_b_git_commit_dispatch,
)
from app.chat.workspace_git import derive_commit_message, git_commit, git_status, git_working_tree_is_clean  # noqa: E402
from app.chat.lane_b_agent import LaneBContext, generate_lane_b_result  # noqa: E402
from app.workspace_agents.execution_policy import role_execution_policy  # noqa: E402
from tests.support.git_repo_helpers import init_git_repo  # noqa: E402


class WorkspaceGitTests(unittest.TestCase):
    def test_git_status_in_temp_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir) / "workspace_alpha"
            root.mkdir()
            subprocess.run(["git", "init"], cwd=root, capture_output=True, check=False)
            (root / "notes.txt").write_text("hello\n", encoding="utf-8")

            with patch.dict("os.environ", {"AXON_WATCH_WORKSPACE_ROOT": tempdir}, clear=False):
                result = git_status("workspace_alpha")

            self.assertTrue(result.success)
            self.assertIn("notes.txt", result.output)

    def test_git_commit_stages_and_commits(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir) / "workspace_alpha"
            root.mkdir()
            init_git_repo(root)
            (root / "notes.txt").write_text("hello\n", encoding="utf-8")
            subprocess.run(["git", "add", "notes.txt"], cwd=root, capture_output=True, check=False)

            with patch.dict("os.environ", {"AXON_WATCH_WORKSPACE_ROOT": tempdir}, clear=False):
                result = git_commit("workspace_alpha", "Add notes")

            self.assertTrue(result.success)
            self.assertIn("Add notes", result.output)


class LaneBGitDispatchTests(unittest.TestCase):
    def test_skips_without_full_access(self) -> None:
        payload = try_lane_b_git_commit_dispatch(
            workspace_id="workspace_alpha",
            user_prompt="commit these changes",
            execution_access="consultative",
        )
        self.assertIsNone(payload)

    def test_derive_commit_message_from_pending_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir) / "workspace_alpha"
            root.mkdir()
            subprocess.run(["git", "init"], cwd=root, capture_output=True, check=False)
            (root / "services" / "control-plane").mkdir(parents=True)
            (root / "services" / "control-plane" / "kairo_voice.py").write_text("# kairo\n")
            (root / "apps" / "console-web").mkdir(parents=True)
            (root / "apps" / "console-web" / "terminal.ts").write_text("// terminal\n")

            with patch.dict("os.environ", {"AXON_WATCH_WORKSPACE_ROOT": tempdir}, clear=False):
                message = derive_commit_message("workspace_alpha")

            self.assertTrue(message.startswith("Add ") or message.startswith("Update "))
            self.assertIn("kairo_voice.py", message)
            self.assertNotIn("Polish", message)

    def test_derive_commit_message_prefers_turn_subject(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir) / "workspace_alpha"
            root.mkdir()
            subprocess.run(["git", "init"], cwd=root, capture_output=True, check=False)
            (root / "notes.txt").write_text("hello\n", encoding="utf-8")

            with patch.dict("os.environ", {"AXON_WATCH_WORKSPACE_ROOT": tempdir}, clear=False):
                message = derive_commit_message(
                    "workspace_alpha",
                    turn_subject="Fix incremental stream-state race in shell onDelta",
                )

            self.assertEqual(message, "Fix incremental stream-state race in shell onDelta")

    def test_derive_commit_message_ignores_bare_commit_intent(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir) / "workspace_alpha"
            root.mkdir()
            subprocess.run(["git", "init"], cwd=root, capture_output=True, check=False)
            (root / "notes.txt").write_text("hello\n", encoding="utf-8")

            with patch.dict("os.environ", {"AXON_WATCH_WORKSPACE_ROOT": tempdir}, clear=False):
                message = derive_commit_message(
                    "workspace_alpha",
                    turn_subject="commit these changes",
                )

            self.assertNotEqual(message, "commit these changes")
            self.assertTrue(message.startswith("Add ") or message.startswith("Update "))

    def test_derive_commit_message_ignores_instructional_operator_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir) / "workspace_alpha"
            root.mkdir()
            subprocess.run(["git", "init"], cwd=root, capture_output=True, check=False)
            (root / "src").mkdir()
            (root / "src" / "PricingPlanCard.tsx").write_text("export {}\n", encoding="utf-8")
            (root / "src" / "ensureAndroidPushChannels.ts").write_text("export {}\n", encoding="utf-8")

            with patch.dict("os.environ", {"AXON_WATCH_WORKSPACE_ROOT": tempdir}, clear=False):
                message = derive_commit_message(
                    "workspace_alpha",
                    turn_subject=(
                        "You should make sure to run the canary:ota - commit and "
                        "do all the things to get the OTA unblocked"
                    ),
                )

            self.assertNotIn("You should", message)
            self.assertNotIn("make sure", message.lower())
            self.assertTrue(
                "OTA canary" in message
                or message.startswith("Add ")
                or message.startswith("Update "),
                message,
            )
            self.assertTrue(
                "PricingPlanCard" in message
                or "ensureAndroidPushChannels" in message
                or "pricing" in message.lower()
                or "push" in message.lower(),
                message,
            )

    def test_derive_commit_message_uses_topic_and_areas_for_large_trees(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir) / "workspace_alpha"
            root.mkdir()
            subprocess.run(["git", "init"], cwd=root, capture_output=True, check=False)
            for path in (
                "components/pricing/PricingPlanCard.tsx",
                "components/pricing/ComparisonTable.tsx",
                "lib/payments/canUploadPopForMonth.ts",
                "lib/notifications/ensureAndroidPushChannels.ts",
                ".github/workflows/ci.yml",
            ):
                target = root / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("x\n", encoding="utf-8")

            with patch.dict("os.environ", {"AXON_WATCH_WORKSPACE_ROOT": tempdir}, clear=False):
                message = derive_commit_message(
                    "workspace_alpha",
                    turn_subject=(
                        "You should make sure to run the canary:ota - commit and "
                        "finish the unblock work."
                    ),
                )

            self.assertTrue(message.startswith("Unblock OTA canary"), message)
            self.assertNotIn("You should", message)
            self.assertTrue(
                "pricing" in message.lower()
                or "payments" in message.lower()
                or "notifications" in message.lower()
                or "CI" in message,
                message,
            )

    def test_skips_questions_about_commits(self) -> None:
        for prompt in (
            "Did you commit and push",
            "did you commit and push?",
            "have the changes been committed?",
            "what did you commit?",
            "I was asking if you did?",
        ):
            payload = try_lane_b_git_commit_dispatch(
                workspace_id="workspace_alpha",
                user_prompt=prompt,
                execution_access="full",
            )
            self.assertIsNone(payload, prompt)

    def test_skips_without_commit_intent(self) -> None:
        payload = try_lane_b_git_commit_dispatch(
            workspace_id="workspace_alpha",
            user_prompt="explain README.md",
            execution_access="full",
        )
        self.assertIsNone(payload)

    def test_skips_when_commit_is_explicitly_out_of_scope(self) -> None:
        payload = try_lane_b_git_commit_dispatch(
            workspace_id="workspace_alpha",
            user_prompt=(
                "Look at Dashpro CI notes and plan agent handling. "
                "I never said anything about committing."
            ),
            execution_access="full",
        )
        self.assertIsNone(payload)

    def test_git_working_tree_is_clean_with_branch_header_only(self) -> None:
        self.assertTrue(git_working_tree_is_clean("## dev...origin/dev"))
        self.assertFalse(git_working_tree_is_clean("## dev...origin/dev\n M notes.txt"))

    def test_derive_commit_message_prefers_plan_after_commit_first(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir) / "workspace_alpha"
            root.mkdir()
            subprocess.run(["git", "init"], cwd=root, capture_output=True, check=False)
            (root / "notes.txt").write_text("hello\n", encoding="utf-8")

            with patch.dict("os.environ", {"AXON_WATCH_WORKSPACE_ROOT": tempdir}, clear=False):
                message = derive_commit_message(
                    "workspace_alpha",
                    turn_subject=(
                        "commit first and then check this plan : "
                        "Slice 1 — Right dock as second brain"
                    ),
                )

            self.assertEqual(message, "Slice 1 — Right dock as second brain")
            self.assertNotIn("check this plan", message.lower())
            self.assertNotIn("notes.txt", message)

    def test_commit_then_refuses_blind_add_on_mixed_tree(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir) / "workspace_alpha"
            root.mkdir()
            subprocess.run(["git", "init"], cwd=root, capture_output=True, check=False)
            for area in ("apps", "services", "docs"):
                (root / area).mkdir()
            for index in range(6):
                (root / "apps" / f"a{index}.ts").write_text("a\n", encoding="utf-8")
                (root / "services" / f"s{index}.py").write_text("s\n", encoding="utf-8")
                (root / "docs" / f"d{index}.md").write_text("d\n", encoding="utf-8")

            with patch.dict("os.environ", {"AXON_WATCH_WORKSPACE_ROOT": tempdir}, clear=False):
                payload = try_lane_b_git_commit_dispatch(
                    workspace_id="workspace_alpha",
                    user_prompt="commit first and then start Slice 1",
                    execution_access="full",
                )

            self.assertIsNotNone(payload)
            assert payload is not None
            self.assertFalse(payload["dispatched"])
            self.assertIn("blind `git add -A`", str(payload["content"]))
            self.assertIsNone(payload.get("continue_prompt"))

    def test_split_commit_then_remainder(self) -> None:
        self.assertEqual(
            split_commit_then_remainder(
                "commit first and then check this plan : Slice 1 — Right dock"
            ),
            "check this plan : Slice 1 — Right dock",
        )
        self.assertEqual(
            split_commit_then_remainder("commit these changes, then rename the seam"),
            "rename the seam",
        )
        self.assertIsNone(split_commit_then_remainder("commit these changes"))
        self.assertIsNone(split_commit_then_remainder("explain README.md"))

    def test_commit_then_continues_to_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir) / "workspace_alpha"
            root.mkdir()
            init_git_repo(root)
            (root / "notes.txt").write_text("hello\n", encoding="utf-8")

            with patch.dict("os.environ", {"AXON_WATCH_WORKSPACE_ROOT": tempdir}, clear=False):
                with patch(
                    "app.chat.lane_b_agent.dispatch_ide_composer",
                    return_value={
                        "content": "Starting Slice 1 — Right dock as second brain",
                        "dispatched": True,
                        "runtime_id": "cursor_local",
                        "runtime_label": "Cursor",
                        "reason": "ok",
                    },
                ) as mock_dispatch:
                    result = generate_lane_b_result(
                        context=LaneBContext(
                            workspace_id="workspace_alpha",
                            composer_mode="agent",
                        ),
                        user_prompt=(
                            "commit first and then check this plan : "
                            "Slice 1 — Right dock as second brain"
                        ),
                        execution_access="full",
                    )

            self.assertIn("Committed successfully", str(result["content"]))
            self.assertIn(":::terminal", str(result["content"]))
            self.assertIn("Starting Slice 1", str(result["content"]))
            mock_dispatch.assert_called_once()
            self.assertIn("Slice 1", mock_dispatch.call_args.kwargs["user_prompt"])
            self.assertNotIn("commit first", mock_dispatch.call_args.kwargs["user_prompt"].lower())

    def test_full_access_commit_dispatch(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir) / "workspace_alpha"
            root.mkdir()
            init_git_repo(root)
            (root / "notes.txt").write_text("hello\n", encoding="utf-8")

            with patch.dict("os.environ", {"AXON_WATCH_WORKSPACE_ROOT": tempdir}, clear=False):
                payload = try_lane_b_git_commit_dispatch(
                    workspace_id="workspace_alpha",
                    user_prompt='commit these changes with message "Ship notes"',
                    execution_access="full",
                )

            self.assertIsNotNone(payload)
            assert payload is not None
            self.assertTrue(payload["dispatched"])
            self.assertIn("Ship notes", str(payload["content"]))
            self.assertIn(":::terminal", str(payload["content"]))
            self.assertIsNone(payload.get("continue_prompt"))

    def test_consultative_role_thread_refuses_commit_even_with_operator_full_access(self) -> None:
        """Regression: an operator message that lands in a watcher thread (write_paths=(),
        execution_access="consultative") must not inherit the operator's own Full Access
        toggle and run a real git add/commit/push. Reproduces the 2026-08-07 DashPro
        incident where a "From the sandbox..." instruction meant for the Lead landed in
        Cass (watcher)'s thread and still committed + pushed to the remote.
        """
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir) / "workspace_alpha"
            root.mkdir()
            init_git_repo(root)
            (root / "notes.txt").write_text("hello\n", encoding="utf-8")

            with patch.dict("os.environ", {"AXON_WATCH_WORKSPACE_ROOT": tempdir}, clear=False):
                payload = try_lane_b_git_commit_dispatch(
                    workspace_id="workspace_alpha",
                    user_prompt='commit these changes with message "Ship notes" and push',
                    execution_access="full",
                    execution_policy=role_execution_policy("watcher"),
                )
                status_after = git_status("workspace_alpha")

            self.assertIsNotNone(payload)
            assert payload is not None
            self.assertFalse(payload["dispatched"])
            self.assertIn("consultative-only", str(payload["content"]))
            # The whole point: nothing was actually staged/committed.
            self.assertIn("notes.txt", status_after.output)

    def test_lead_role_thread_still_commits_with_operator_full_access(self) -> None:
        """A role whose baseline execution_access is "full" (e.g. lead) is unaffected."""
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir) / "workspace_alpha"
            root.mkdir()
            init_git_repo(root)
            (root / "notes.txt").write_text("hello\n", encoding="utf-8")

            with patch.dict("os.environ", {"AXON_WATCH_WORKSPACE_ROOT": tempdir}, clear=False):
                payload = try_lane_b_git_commit_dispatch(
                    workspace_id="workspace_alpha",
                    user_prompt='commit these changes with message "Ship notes"',
                    execution_access="full",
                    execution_policy=role_execution_policy("lead"),
                )

            self.assertIsNotNone(payload)
            assert payload is not None
            self.assertTrue(payload["dispatched"])

    def test_requires_explicit_message_when_generic_fallback_would_be_used(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir) / "workspace_alpha"
            root.mkdir()
            subprocess.run(["git", "init"], cwd=root, capture_output=True, check=False)
            (root / "misc.py").write_text("x = 1\n", encoding="utf-8")

            with patch.dict("os.environ", {"AXON_WATCH_WORKSPACE_ROOT": tempdir}, clear=False):
                with patch(
                    "app.chat.lane_b_git_dispatch.derive_commit_message",
                    return_value="Update via Axon-X",
                ):
                    payload = try_lane_b_git_commit_dispatch(
                        workspace_id="workspace_alpha",
                        user_prompt="commit these changes",
                        execution_access="full",
                    )

            self.assertIsNotNone(payload)
            assert payload is not None
            self.assertFalse(payload["dispatched"])
            self.assertIn("explicit commit message", str(payload["content"]))

    def test_commit_and_push_dispatch_reports_push(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            remote = Path(tempdir) / "remote.git"
            subprocess.run(
                ["git", "init", "--bare", str(remote)], capture_output=True, check=False
            )
            root = Path(tempdir) / "workspace_alpha"
            root.mkdir()
            subprocess.run(["git", "init", "-b", "main"], cwd=root, capture_output=True, check=False)
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=root,
                capture_output=True,
                check=False,
            )
            subprocess.run(
                ["git", "config", "user.name", "Axon Test"],
                cwd=root,
                capture_output=True,
                check=False,
            )
            subprocess.run(
                ["git", "remote", "add", "origin", str(remote)],
                cwd=root,
                capture_output=True,
                check=False,
            )
            (root / "notes.txt").write_text("hello\n", encoding="utf-8")
            subprocess.run(["git", "add", "-A"], cwd=root, capture_output=True, check=False)
            subprocess.run(
                ["git", "commit", "-m", "seed"], cwd=root, capture_output=True, check=False
            )
            subprocess.run(
                ["git", "push", "-u", "origin", "main"],
                cwd=root,
                capture_output=True,
                check=False,
            )
            (root / "notes.txt").write_text("hello again\n", encoding="utf-8")

            with patch.dict("os.environ", {"AXON_WATCH_WORKSPACE_ROOT": tempdir}, clear=False):
                payload = try_lane_b_git_commit_dispatch(
                    workspace_id="workspace_alpha",
                    user_prompt='commit and push with message "Ship again"',
                    execution_access="full",
                )

            self.assertIsNotNone(payload)
            assert payload is not None
            self.assertTrue(payload["dispatched"])
            self.assertIn("Pushed to the remote", str(payload["content"]))


if __name__ == "__main__":
    unittest.main()
