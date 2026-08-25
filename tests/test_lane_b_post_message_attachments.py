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

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.chat.lane_b_post_message import _localize_attachment_paths_for_sandbox  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
