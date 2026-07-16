"""Live acceptance for the first real child-project workspace binding (DashPro).

Requires `./scripts/dev/up.sh` and DashPro checkout at the configured path.

Run:
  python3 -m unittest tests.test_child_project_workspace_acceptance
  ./scripts/verify/child-project-workspace.sh
"""

from __future__ import annotations

import json
import os
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from tests.support.live_chat_mutations import (
    LIVE_CHAT_MUTATION_SKIP_REASON,
    live_chat_mutations_allowed,
)

CONTROL_PLANE_BASE = os.environ.get(
    "AXON_WATCH_CONTROL_PLANE_BASE",
    "http://127.0.0.1:8787",
)
WORKSPACE_DASHPRO = "workspace_dashpro"
WORKSPACE_AXON_WATCH = "workspace_axon_watch"
REPO_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_DASHPRO_ROOT = Path("/home/edp/Projectx/product/dashpro").resolve()


def _request(
    method: str,
    url: str,
    body: dict | None = None,
) -> tuple[int, dict | list | str]:
    data = None if body is None else json.dumps(body).encode()
    headers = {"Content-Type": "application/json"} if body is not None else {}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
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
@unittest.skipUnless(
    EXPECTED_DASHPRO_ROOT.is_dir(),
    "DashPro child project not present at configured path",
)
class ChildProjectWorkspaceAcceptance(unittest.TestCase):
    def test_dashpro_workspace_is_bound_with_project_path(self) -> None:
        status, payload = _request("GET", f"{CONTROL_PLANE_BASE}/api/workspaces/{WORKSPACE_DASHPRO}")
        self.assertEqual(200, status)
        self.assertIsInstance(payload, dict)
        assert isinstance(payload, dict)
        self.assertEqual("project_path", payload.get("connection_kind"))
        project_root = str(payload.get("project_root", ""))
        self.assertTrue(project_root.endswith("dashpro"))

    @unittest.skipUnless(live_chat_mutations_allowed(), LIVE_CHAT_MUTATION_SKIP_REASON)
    def test_git_status_runs_in_bound_dashpro_project(self) -> None:
        status, payload = _request(
            "POST",
            f"{CONTROL_PLANE_BASE}/api/chat/messages",
            {"workspace_id": WORKSPACE_DASHPRO, "content": "git status"},
        )
        self.assertEqual(200, status)
        self.assertIsInstance(payload, dict)
        messages = payload.get("messages", [])
        agent_messages = [message for message in messages if message.get("role") == "agent"]
        self.assertTrue(agent_messages)
        agent_copy = str(agent_messages[-1]["content"]).lower()
        self.assertNotIn("unsupported command", agent_copy)
        self.assertTrue(
            "on branch" in agent_copy
            or "git status" in agent_copy
            or "nothing to commit" in agent_copy
            or "executed" in agent_copy,
            msg=agent_copy[:400],
        )

    def test_handoff_from_watch_to_dashpro(self) -> None:
        status, payload = _request(
            "POST",
            f"{CONTROL_PLANE_BASE}/api/workspaces/{WORKSPACE_AXON_WATCH}/handoffs",
            {
                "target_workspace_id": WORKSPACE_DASHPRO,
                "task": "Child-project workspace handoff",
                "reason": "Phase E child-project proof",
            },
        )
        self.assertEqual(200, status)
        self.assertIsInstance(payload, dict)
        handoff = payload.get("handoff")
        self.assertIsInstance(handoff, dict)
        assert isinstance(handoff, dict)
        self.assertEqual(WORKSPACE_AXON_WATCH, handoff.get("source_workspace_id"))
        self.assertEqual(WORKSPACE_DASHPRO, handoff.get("target_workspace_id"))


if __name__ == "__main__":
    unittest.main()
