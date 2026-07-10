from __future__ import annotations

import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.cli_runtime.generated_image_paths import (  # noqa: E402
    image_paths_from_markdown,
    image_paths_from_tool_call_event,
)
from app.chat.lane_b_image_attachments import (  # noqa: E402
    ingest_agent_generated_images,
    resolve_generated_image_path,
)
from app.cli_runtime.cursor_stream_events import CursorStreamAssembler  # noqa: E402
from app.main import app  # noqa: E402
from app.persistence import attachment_store, chat_store  # noqa: E402


def _tiny_png_bytes() -> bytes:
    return (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
        b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
        b"\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )


def _generate_image_event(path: str) -> dict:
    return {
        "type": "tool_call",
        "subtype": "completed",
        "tool_call": {
            "generateImageToolCall": {
                "args": {"description": "mockup", "filename": Path(path).name},
                "result": {
                    "success": {
                        "path": path,
                    }
                },
            }
        },
    }


class LaneBImageAttachmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self._root = Path(self._tmpdir.name)
        os.environ["AXON_WATCH_CONTROL_PLANE_DB"] = str(self._root / "control-plane.sqlite3")
        os.environ["AXON_WATCH_STATE_DIR"] = str(self._root / "state")
        chat_store.reset_store()

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_image_paths_from_generate_image_tool_call(self) -> None:
        paths = image_paths_from_tool_call_event(
            _generate_image_event("/tmp/mockup.png"),
        )
        self.assertEqual(["/tmp/mockup.png"], paths)

    def test_image_paths_from_markdown(self) -> None:
        paths = image_paths_from_markdown(
            "Here is the mockup:\n\n![mockup](assets/axon-x-mobile.png)"
        )
        self.assertEqual(["assets/axon-x-mobile.png"], paths)

    def test_resolve_generated_image_path_prefers_workspace_assets(self) -> None:
        workspace_root = self._root / "workspace"
        assets_dir = workspace_root / "assets"
        assets_dir.mkdir(parents=True)
        image_path = assets_dir / "mockup.png"
        image_path.write_bytes(_tiny_png_bytes())

        resolved = resolve_generated_image_path(
            "assets/mockup.png",
            workspace_root=workspace_root,
        )
        self.assertEqual(image_path.resolve(), resolved)

    def test_ingest_agent_generated_images_binds_to_message(self) -> None:
        workspace_root = self._root / "workspace"
        assets_dir = workspace_root / "assets"
        assets_dir.mkdir(parents=True)
        image_path = assets_dir / "mockup.png"
        image_path.write_bytes(_tiny_png_bytes())

        with patch(
            "app.chat.lane_b_image_attachments.resolve_workspace_root",
            return_value=workspace_root,
        ):
            bound = ingest_agent_generated_images(
                workspace_id="workspace_alpha",
                message_id="message_agent_1",
                thread_id="thread_1",
                image_paths=["assets/mockup.png"],
                created_at="2026-07-09T17:00:00Z",
            )

        self.assertEqual(1, len(bound))
        self.assertEqual("mockup.png", bound[0]["filename"])
        self.assertTrue(str(bound[0]["url"]).startswith("/api/chat/attachments/"))

    def test_stream_assembler_collects_generated_image_paths(self) -> None:
        assembler = CursorStreamAssembler(workspace_root=str(self._root))
        assembler.feed_line(
            '{"type":"tool_call","subtype":"completed","tool_call":{"generateImageToolCall":'
            '{"args":{"description":"mockup"},"result":{"success":{"path":"assets/mockup.png"}}}}}'
        )
        self.assertEqual(("assets/mockup.png",), assembler.generated_image_paths)

    def test_stream_assembler_emits_image_block(self) -> None:
        assembler = CursorStreamAssembler(workspace_root=str(self._root))
        assembler.feed_line(
            '{"type":"tool_call","subtype":"completed","tool_call":{"generateImageToolCall":'
            '{"args":{"description":"mockup"},"result":{"success":{"path":"assets/mockup.png"}}}}}'
        )
        content = assembler.finalize()
        self.assertIn(":::image assets/mockup.png", content)

    def test_lane_b_message_attaches_generated_images(self) -> None:
        workspace_root = self._root / "workspace"
        assets_dir = workspace_root / "assets"
        assets_dir.mkdir(parents=True)
        image_path = assets_dir / "mockup.png"
        image_path.write_bytes(_tiny_png_bytes())

        client = TestClient(app)
        with patch(
            "app.chat.lane_b_image_attachments.resolve_workspace_root",
            return_value=workspace_root,
        ), patch(
            "app.chat.service.generate_lane_b_result",
            return_value={
                "content": "Mockup ready.\n\n![mockup](assets/mockup.png)",
                "dispatched": True,
                "runtime_id": "cursor_local",
                "runtime_label": "Cursor CLI (local)",
                "reason": "",
                "generated_image_paths": ["assets/mockup.png"],
            },
        ):
            response = client.post(
                "/api/chat/messages",
                json={
                    "workspace_id": "workspace_alpha",
                    "content": "Generate a mockup",
                    "composer_mode": "ask",
                },
            )

        self.assertEqual(200, response.status_code)
        thread_id = response.json()["thread_id"]
        history = client.get(f"/api/chat/threads/{thread_id}/history").json()
        agent = next(item for item in history["items"] if item["role"] == "agent")
        attachments = agent.get("attachments", [])
        self.assertEqual(1, len(attachments))
        self.assertEqual("mockup.png", attachments[0]["filename"])

        show = client.get(attachments[0]["url"])
        self.assertEqual(200, show.status_code)
        self.assertEqual("image/png", show.headers.get("content-type"))


if __name__ == "__main__":
    unittest.main()
