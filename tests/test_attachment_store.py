"""Unit tests for chat attachment persistence and mime validation."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.persistence import attachment_store, chat_store  # noqa: E402


class AttachmentStoreTests(unittest.TestCase):
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

    def test_save_upload_accepts_pdf_and_csv(self) -> None:
        pdf = attachment_store.save_upload(
            workspace_id="workspace_alpha",
            filename="brief.pdf",
            mime_type="application/pdf",
            data=b"%PDF-1.4 sample",
            created_at="2026-07-20T14:00:00Z",
        )
        self.assertEqual("application/pdf", pdf["mime_type"])

        csv = attachment_store.save_upload(
            workspace_id="workspace_alpha",
            filename="report.csv",
            mime_type="text/csv",
            data=b"a,b\n1,2\n",
            created_at="2026-07-20T14:00:01Z",
        )
        self.assertEqual("text/csv", csv["mime_type"])

    def test_save_upload_infers_csv_from_octet_stream_filename(self) -> None:
        record = attachment_store.save_upload(
            workspace_id="workspace_alpha",
            filename="ledger.csv",
            mime_type="application/octet-stream",
            data=b"sku,qty\nA,3\n",
            created_at="2026-07-20T14:00:02Z",
        )
        self.assertEqual("text/csv", record["mime_type"])

    def test_save_upload_infers_markdown_from_extension(self) -> None:
        record = attachment_store.save_upload(
            workspace_id="workspace_alpha",
            filename="notes.md",
            mime_type="application/octet-stream",
            data=b"# Notes\n",
            created_at="2026-07-20T14:00:03Z",
        )
        self.assertEqual("text/markdown", record["mime_type"])

    def test_save_upload_rejects_unsupported_types(self) -> None:
        with self.assertRaises(attachment_store.AttachmentValidationError):
            attachment_store.save_upload(
                workspace_id="workspace_alpha",
                filename="payload.exe",
                mime_type="application/x-msdownload",
                data=b"MZ",
                created_at="2026-07-20T14:00:04Z",
            )

    def test_bind_and_list_attachments_for_message(self) -> None:
        record = attachment_store.save_upload(
            workspace_id="workspace_alpha",
            filename="notes.txt",
            mime_type="text/plain",
            data=b"hello",
            created_at="2026-07-20T14:00:05Z",
        )
        bound = attachment_store.bind_attachments_to_message(
            attachment_ids=[record["attachment_id"]],
            workspace_id="workspace_alpha",
            message_id="message_operator_abc",
            thread_id="thread_ide_abc",
        )
        self.assertEqual(1, len(bound))
        self.assertEqual("message_operator_abc", bound[0]["message_id"])
        self.assertEqual("thread_ide_abc", bound[0]["thread_id"])

        grouped = attachment_store.list_attachments_for_messages(["message_operator_abc"])
        self.assertIn("message_operator_abc", grouped)
        self.assertEqual(record["attachment_id"], grouped["message_operator_abc"][0]["attachment_id"])

        serialized = attachment_store.serialize_attachment(bound[0])
        self.assertEqual(f"/api/chat/attachments/{record['attachment_id']}", serialized["url"])

        with self.assertRaises(attachment_store.AttachmentValidationError):
            attachment_store.bind_attachments_to_message(
                attachment_ids=[record["attachment_id"]],
                workspace_id="workspace_alpha",
                message_id="message_operator_def",
                thread_id="thread_ide_def",
            )


if __name__ == "__main__":
    unittest.main()
