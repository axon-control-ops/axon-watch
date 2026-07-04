from __future__ import annotations

import json
import sys
import unittest
from collections.abc import AsyncIterator
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.live_events import _format_sse  # noqa: E402
from app.main import app  # noqa: E402


async def _connected_only_stream() -> AsyncIterator[bytes]:
    yield _format_sse({"type": "connected"})


class ControlPlaneLiveEventsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def test_live_events_returns_event_stream_with_connected_event(self) -> None:
        with patch("app.live_events.live_events_stream", _connected_only_stream):
            response = self.client.get("/api/live/events")

        self.assertEqual(200, response.status_code)
        content_type = response.headers.get("content-type", "")
        self.assertIn("text/event-stream", content_type)

        first_line = response.text.splitlines()[0]
        self.assertTrue(first_line.startswith("data: "))
        payload = json.loads(first_line.removeprefix("data: "))
        self.assertEqual({"type": "connected"}, payload)


if __name__ == "__main__":
    unittest.main()
