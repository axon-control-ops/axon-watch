"""Attachment paths must be reachable from inside the agent's own sandbox.

Regression: context.image_paths carries real absolute host paths under the
control plane's own state directory (attachment_store._attachments_root()).
An agent executing in an isolated sandbox checkout has no access to that
directory, so handing it the raw path guarantees "No such file or directory"
the moment it tries to read it — confirmed live against a real workspace.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.chat.lane_b_post_message import _localize_attachment_paths_for_sandbox  # noqa: E402
from app.chat.lane_b_post_message import post_lane_b_message  # noqa: E402
from app.persistence import attachment_store, chat_store, run_store  # noqa: E402


class LocalizeAttachmentPathsForSandboxTests(unittest.TestCase):
    def test_copies_attachment_into_sandbox_and_rewrites_path(self) -> None:
        with tempfile.TemporaryDirectory() as state_dir, tempfile.TemporaryDirectory() as sandbox_dir:
            source = Path(state_dir) / "menu.jpg"
            source.write_bytes(b"fake-image-bytes")
            sandbox_root = Path(sandbox_dir)

            localized = _localize_attachment_paths_for_sandbox(
                (str(source),),
                sandbox_workspace_root=sandbox_root,
            )

            self.assertEqual(1, len(localized))
            localized_path = Path(localized[0])
            self.assertTrue(localized_path.is_relative_to(sandbox_root))
            self.assertTrue(localized_path.is_file())
            self.assertEqual(b"fake-image-bytes", localized_path.read_bytes())
            # The original host-only path is no longer what the agent is told.
            self.assertNotEqual(str(source), localized[0])

    def test_no_sandbox_leaves_paths_unchanged(self) -> None:
        # Consultative/Ask-mode dispatches may have no isolated sandbox at all
        # (resolve_sandbox_workspace_root returns None) — nothing to localize.
        paths = ("/some/host/path/image.png",)
        self.assertEqual(
            paths,
            _localize_attachment_paths_for_sandbox(paths, sandbox_workspace_root=None),
        )

    def test_missing_source_file_fails_open_to_original_path(self) -> None:
        with tempfile.TemporaryDirectory() as sandbox_dir:
            missing = "/tmp/definitely-does-not-exist-attachment.png"
            localized = _localize_attachment_paths_for_sandbox(
                (missing,),
                sandbox_workspace_root=Path(sandbox_dir),
            )
            self.assertEqual((missing,), localized)

    def test_empty_paths_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as sandbox_dir:
            self.assertEqual(
                (),
                _localize_attachment_paths_for_sandbox((), sandbox_workspace_root=Path(sandbox_dir)),
            )


class StreamingAttachmentPathTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)
        chat_store.reset_store()
        self.addCleanup(chat_store.reset_store)

    def test_stream_job_receives_sandbox_localized_attachment_paths(self) -> None:
        with tempfile.TemporaryDirectory() as sandbox_dir:
            record = attachment_store.save_upload(
                workspace_id="workspace_screens",
                filename="screen.png",
                mime_type="image/png",
                data=b"\x89PNG\r\n\x1a\n",
                created_at="2026-08-26T16:40:00Z",
            )
            original_path = str(record["storage_path"])
            sandbox_root = Path(sandbox_dir)

            with (
                patch(
                    "app.cli_runtime.composer_sandbox.resolve_sandbox_execution",
                    return_value=(sandbox_root, "full"),
                ),
                patch(
                    "app.chat.lane_b_post_message.resolve_lane_b_agent_run",
                    return_value={"run_id": "run_attachment_stream", "phase": "executing"},
                ),
                patch("app.chat.service._lane_b_streaming_enabled", return_value=True),
            ):
                payload = post_lane_b_message(
                    workspace_id="workspace_screens",
                    content="Please inspect the attached screenshot.",
                    thread_id=None,
                    run_id=None,
                    composer_mode="plan",
                    active_file_path=None,
                    editor_selection=None,
                    terminal_snippet=None,
                    attachment_ids=[str(record["attachment_id"])],
                    runtime_target=None,
                    runtime_model=None,
                    execution_access="full",
                    kairo_session_id=None,
                    created_at="2026-08-26T16:41:00Z",
                )

            stream_job = payload.get("_stream_job")
            self.assertIsNotNone(stream_job)
            localized = tuple(getattr(stream_job, "image_paths"))
            self.assertEqual(1, len(localized))
            self.assertNotEqual(original_path, localized[0])
            self.assertTrue(Path(localized[0]).is_relative_to(sandbox_root))
            self.assertTrue(Path(localized[0]).is_file())


if __name__ == "__main__":
    unittest.main()
