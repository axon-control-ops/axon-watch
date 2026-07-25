"""TEST-1 live acceptance for real project/workspace bindings on the dev stack.

Requires `./scripts/dev/up.sh` (ports 4173 / 8787 / 8788) and sibling repo
`../axon-local` when using the default bindings file.

Run:
  python3 -m unittest tests.test_test1_workspace_project_connection_acceptance
  ./scripts/verify/test1-workspace-project-connection.sh
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

WORKSPACE_AXON_LOCAL = "workspace_axon_local"
WORKSPACE_AXON_WATCH = "workspace_axon_watch"
CONTROL_PLANE_BASE = os.environ.get(
    "AXON_WATCH_CONTROL_PLANE_BASE",
    "http://127.0.0.1:8787",
)
REPO_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_AXON_LOCAL_ROOT = (REPO_ROOT.parent / "axon-local").resolve()


def _request(method: str, url: str, body: dict | None = None) -> tuple[int, dict | list | str]:
    data = None if body is None else json.dumps(body).encode()
    headers = {"Content-Type": "application/json"} if body is not None else {}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
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


def _workspace_record(workspace_id: str) -> dict | None:
    status, payload = _request("GET", f"{CONTROL_PLANE_BASE}/api/workspaces/{workspace_id}")
    if status != 200 or not isinstance(payload, dict):
        return None
    return payload


@unittest.skipUnless(_stack_available(), "dev stack not running on control-plane base URL")
@unittest.skipUnless(
    EXPECTED_AXON_LOCAL_ROOT.is_dir(),
    "sibling axon-local repo not present for default bindings",
)
class Test1WorkspaceProjectConnectionAcceptance(unittest.TestCase):
    def test_bound_workspaces_are_listed_with_project_metadata(self) -> None:
        status, payload = _request("GET", f"{CONTROL_PLANE_BASE}/api/workspaces")
        self.assertEqual(200, status)
        items = payload.get("items") if isinstance(payload, dict) else payload
        self.assertIsInstance(items, list)

        by_id = {item["workspace_id"]: item for item in items}
        self.assertIn(WORKSPACE_AXON_LOCAL, by_id)
        self.assertIn(WORKSPACE_AXON_WATCH, by_id)

        axon_local = by_id[WORKSPACE_AXON_LOCAL]
        self.assertEqual("project_path", axon_local.get("connection_kind"))
        self.assertEqual(str(EXPECTED_AXON_LOCAL_ROOT), axon_local.get("project_root"))
        self.assertEqual("axon-local", axon_local.get("display_name"))

        axon_watch = by_id[WORKSPACE_AXON_WATCH]
        self.assertEqual("project_path", axon_watch.get("connection_kind"))
        self.assertEqual(str(REPO_ROOT.resolve()), axon_watch.get("project_root"))

    def test_workspace_show_returns_bound_project_root(self) -> None:
        record = _workspace_record(WORKSPACE_AXON_LOCAL)
        self.assertIsNotNone(record)
        assert record is not None
        self.assertEqual(WORKSPACE_AXON_LOCAL, record["workspace_id"])
        self.assertEqual("project_path", record.get("connection_kind"))
        self.assertEqual(str(EXPECTED_AXON_LOCAL_ROOT), record.get("project_root"))

    def test_isolated_workspace_still_reports_isolated_root(self) -> None:
        record = _workspace_record("workspace_alpha")
        self.assertIsNotNone(record)
        assert record is not None
        self.assertEqual("isolated_root", record.get("connection_kind"))
        self.assertNotIn("project_root", record)

    @unittest.skipUnless(live_chat_mutations_allowed(), LIVE_CHAT_MUTATION_SKIP_REASON)
    def test_git_status_runs_in_bound_axon_local_project(self) -> None:
        status, payload = _request(
            "POST",
            f"{CONTROL_PLANE_BASE}/api/chat/messages",
            {"workspace_id": WORKSPACE_AXON_LOCAL, "content": "git status"},
        )
        self.assertEqual(200, status)
        self.assertIsInstance(payload, dict)
        messages = payload.get("messages", [])
        agent_messages = [message for message in messages if message.get("role") == "agent"]
        self.assertTrue(agent_messages)
        agent_copy = agent_messages[-1]["content"].lower()
        self.assertNotIn("unsupported command", agent_copy)
        self.assertTrue(
            "on branch" in agent_copy
            or "git status" in agent_copy
            or "nothing to commit" in agent_copy
            or "executed" in agent_copy
        )


if __name__ == "__main__":
    unittest.main()
