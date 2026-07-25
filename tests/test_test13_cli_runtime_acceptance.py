"""TEST-13 live acceptance for CLI runtime status and IDE Lane B routing.

Requires `./scripts/dev/up.sh` (ports 4173 / 8787 / 8788).

Run:
  python3 -m unittest tests.test_test13_cli_runtime_acceptance
  ./scripts/verify/test13-cli-runtime.sh
"""

from __future__ import annotations

import json
import os
import time
import unittest
import urllib.error
import urllib.request

CONTROL_PLANE_BASE = os.environ.get(
    "AXON_WATCH_CONTROL_PLANE_BASE",
    "http://127.0.0.1:8787",
)
WORKSPACE_ALPHA = "workspace_alpha"


def _request(
    method: str,
    url: str,
    body: dict | None = None,
) -> tuple[int, dict | list | str]:
    data = None if body is None else json.dumps(body).encode()
    headers = {"Content-Type": "application/json"} if body is not None else {}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            raw = response.read().decode()
            if not raw:
                return response.status, {}
            try:
                return response.status, json.loads(raw)
            except json.JSONDecodeError:
                return response.status, raw
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, raw


def _stack_available() -> bool:
    status, _ = _request("GET", f"{CONTROL_PLANE_BASE}/api/health")
    return status == 200


@unittest.skipUnless(_stack_available(), "dev stack not running on control-plane base URL")
class Test13CliRuntimeAcceptance(unittest.TestCase):
    def test_runtime_status_route_returns_catalog_shape(self) -> None:
        status, payload = _request("GET", f"{CONTROL_PLANE_BASE}/api/runtime/status")
        self.assertEqual(200, status)
        self.assertIsInstance(payload, dict)
        self.assertIn("default_runtime", payload)
        self.assertIn("local", payload)
        self.assertIn("cloud", payload)

    def _await_agent_message(self, thread_id: str, message_id: str, timeout_seconds: int = 120) -> str:
        """Poll thread history until the streaming agent reply lands."""
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            status, history = _request(
                "GET",
                f"{CONTROL_PLANE_BASE}/api/chat/threads/{thread_id}/history",
            )
            if status == 200 and isinstance(history, dict):
                for item in history.get("items", []):
                    if item.get("message_id") == message_id and str(item.get("content") or "").strip():
                        return str(item["content"])
            time.sleep(2)
        return ""

    def test_lane_b_ask_request_returns_agent_reply_without_dispatch(self) -> None:
        status, payload = _request(
            "POST",
            f"{CONTROL_PLANE_BASE}/api/chat/messages",
            {
                "workspace_id": WORKSPACE_ALPHA,
                "content": "Explain this workspace briefly.",
                "composer_mode": "ask",
            },
        )
        self.assertEqual(200, status)
        self.assertIsInstance(payload, dict)
        self.assertFalse(payload.get("dispatched"))
        self.assertIsNone(payload.get("run"))
        messages = payload.get("messages", [])
        self.assertEqual(3, len(messages))
        self.assertIn("Lane B (ask)", str(messages[1].get("content") or ""))

        agent_content = str(messages[2].get("content") or "").strip()
        if not agent_content and payload.get("streaming"):
            # Lane B streams the reply after the POST returns; wait for it.
            agent_content = self._await_agent_message(
                str(payload.get("thread_id") or ""),
                str(payload.get("stream_agent_message_id") or ""),
            ).strip()
        self.assertTrue(agent_content)


if __name__ == "__main__":
    unittest.main()
