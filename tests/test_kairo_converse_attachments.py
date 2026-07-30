"""VAXON converse attachment path resolution."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.kairo.converse_attachments import (  # noqa: E402
    ConverseAttachmentError,
    prepare_converse_attachment_paths,
)
from app.persistence import attachment_store, chat_store  # noqa: E402


class ConverseAttachmentPathsTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        os.environ["AXON_WATCH_CONTROL_PLANE_DB"] = os.path.join(
            self._tmpdir.name,
            "control-plane.sqlite3",
        )
        os.environ["AXON_WATCH_STATE_DIR"] = os.path.join(self._tmpdir.name, "state")
        chat_store.reset_store()

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_empty_ids_return_empty(self) -> None:
        self.assertEqual(
            (),
            prepare_converse_attachment_paths(attachment_ids=None, workspace_id="ws"),
        )

    def test_resolves_workspace_owned_paths(self) -> None:
        record = attachment_store.save_upload(
            workspace_id="workspace_axon_watch",
            filename="shot.png",
            mime_type="image/png",
            data=b"\x89PNG\r\n\x1a\n",
            created_at="2026-07-28T12:00:00Z",
        )
        paths = prepare_converse_attachment_paths(
            attachment_ids=[record["attachment_id"]],
            workspace_id="workspace_axon_watch",
        )
        self.assertEqual(1, len(paths))
        self.assertTrue(Path(paths[0]).exists())

    def test_rejects_foreign_workspace(self) -> None:
        record = attachment_store.save_upload(
            workspace_id="workspace_axon_watch",
            filename="shot.png",
            mime_type="image/png",
            data=b"\x89PNG\r\n\x1a\n",
            created_at="2026-07-28T12:00:00Z",
        )
        with self.assertRaises(ConverseAttachmentError):
            prepare_converse_attachment_paths(
                attachment_ids=[record["attachment_id"]],
                workspace_id="workspace_dashpro",
            )


if __name__ == "__main__":
    unittest.main()
