import unittest

import sys
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.chat.stream_hub import format_sse, publish_chat_stream_event  # noqa: E402


class ChatStreamHubTests(unittest.TestCase):
    def test_format_sse_serializes_payload(self) -> None:
        payload = {"type": "chat_stream_delta", "content": "hello"}
        rendered = format_sse(payload).decode("utf-8")
        self.assertTrue(rendered.startswith("data: "))
        self.assertIn('"type":"chat_stream_delta"', rendered.replace(" ", ""))

    def test_publish_chat_stream_event_ignores_blank_thread(self) -> None:
        publish_chat_stream_event("", {"type": "chat_stream_delta", "content": "ignored"})


if __name__ == "__main__":
    unittest.main()
