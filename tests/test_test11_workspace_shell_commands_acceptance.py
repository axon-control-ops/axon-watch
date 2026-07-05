"""TEST-11 live acceptance for bounded workspace shell commands.

Requires `./scripts/dev/up.sh` (ports 4173 / 8787 / 8788).

Run:
  python3 -m unittest tests.test_test11_workspace_shell_commands_acceptance
  ./scripts/verify/test11-workspace-shell-commands.sh
"""

from __future__ import annotations

import json
import os
import unittest
import urllib.error
import urllib.request

CONTROL_PLANE_BASE = os.environ.get(
    "AXON_WATCH_CONTROL_PLANE_BASE",
    "http://127.0.0.1:8787",
)
WORKSPACE_AXON_WATCH = "workspace_axon_watch"


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


def _agent_copy(payload: dict) -> str:
    messages = payload.get("messages", [])
    agent_messages = [message for message in messages if message.get("role") == "agent"]
    if not agent_messages:
        raise AssertionError("expected agent message in chat response")
    return str(agent_messages[-1]["content"])


@unittest.skipUnless(_stack_available(), "dev stack not running on control-plane base URL")
class Test11WorkspaceShellCommandsAcceptance(unittest.TestCase):
    def test_run_check_health_script_via_shell_command(self) -> None:
        status, payload = _request(
            "POST",
            f"{CONTROL_PLANE_BASE}/api/chat/messages",
            {
                "workspace_id": WORKSPACE_AXON_WATCH,
                "content": "run ./scripts/dev/check-health.sh",
            },
        )
        self.assertEqual(200, status)
        self.assertIsInstance(payload, dict)
        agent_copy = _agent_copy(payload).lower()
        self.assertNotIn("unsupported command", agent_copy)
        self.assertIn("executed", agent_copy)
        self.assertTrue(
            "health" in agent_copy or "ok" in agent_copy or "pass" in agent_copy,
            msg=agent_copy[:400],
        )

    def test_check_health_shortcut_without_run_prefix(self) -> None:
        status, payload = _request(
            "POST",
            f"{CONTROL_PLANE_BASE}/api/chat/messages",
            {
                "workspace_id": WORKSPACE_AXON_WATCH,
                "content": "check-health",
            },
        )
        self.assertEqual(200, status)
        self.assertIsInstance(payload, dict)
        agent_copy = _agent_copy(payload).lower()
        self.assertNotIn("unsupported command", agent_copy)
        self.assertIn("shell_command", agent_copy)

    def test_run_npm_test_via_shell_command(self) -> None:
        status, payload = _request(
            "POST",
            f"{CONTROL_PLANE_BASE}/api/chat/messages",
            {
                "workspace_id": WORKSPACE_AXON_WATCH,
                "content": "run npm test",
            },
        )
        self.assertEqual(200, status)
        self.assertIsInstance(payload, dict)
        agent_copy = _agent_copy(payload).lower()
        self.assertNotIn("unsupported command", agent_copy)
        self.assertIn("shell_command", agent_copy)
        self.assertIn("executed", agent_copy)


if __name__ == "__main__":
    unittest.main()
