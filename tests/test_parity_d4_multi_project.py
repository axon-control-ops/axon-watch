"""P-D4 multi-project / second bound workspace parity tests."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from fastapi.testclient import TestClient

from tests.support.control_plane_db import isolate_control_plane_db

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTROL_PLANE_ROOT = REPO_ROOT / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.main import app  # noqa: E402
from app.persistence import handoff_store, run_store  # noqa: E402

WORKSPACE_AXON_LOCAL = "workspace_axon_local"
WORKSPACE_AXON_WATCH = "workspace_axon_watch"
CONTROL_PLANE_BASE = os.environ.get(
    "AXON_WATCH_CONTROL_PLANE_BASE",
    "http://127.0.0.1:8787",
)
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
    try:
        status, _ = _request("GET", f"{CONTROL_PLANE_BASE}/api/health")
        return status == 200
    except urllib.error.URLError:
        return False


class ParityD4MultiProjectTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)
        handoff_store.reset_store()
        self.addCleanup(handoff_store.reset_store)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def test_default_verify_wiring_includes_parity_d4_tests(self) -> None:
        from tests.verify_contract_wiring import contract_verify_wiring_surface

        verify_script = contract_verify_wiring_surface()
        self.assertIn("tests.test_parity_d4_multi_project", verify_script)

    def test_default_bindings_include_watch_local_and_plans_workspaces(self) -> None:
        bindings = json.loads(
            (REPO_ROOT / "config" / "workspace-project-bindings.json").read_text(encoding="utf-8")
        )
        bound = bindings["bindings"]
        self.assertIn(WORKSPACE_AXON_LOCAL, bound)
        self.assertIn(WORKSPACE_AXON_WATCH, bound)
        self.assertIn("workspace_dashpro", bound)

    def test_workspace_catalog_lists_both_bound_projects(self) -> None:
        response = self.client.get("/api/workspaces")
        self.assertEqual(200, response.status_code)
        items = response.json()["items"]
        by_id = {item["workspace_id"]: item for item in items}
        self.assertIn(WORKSPACE_AXON_LOCAL, by_id)
        self.assertIn(WORKSPACE_AXON_WATCH, by_id)
        self.assertIn("workspace_dashpro", by_id)
        self.assertEqual("project_path", by_id[WORKSPACE_AXON_LOCAL]["connection_kind"])
        self.assertEqual("project_path", by_id[WORKSPACE_AXON_WATCH]["connection_kind"])

    def test_handoff_from_watch_to_dashpro_returns_project_path_summary(self) -> None:
        response = self.client.post(
            f"/api/workspaces/{WORKSPACE_AXON_WATCH}/handoffs",
            json={
                "target_workspace_id": "workspace_dashpro",
                "task": "Child-project handoff proof",
                "reason": "multi-project contract",
            },
        )
        self.assertEqual(200, response.status_code)
        payload = response.json()
        handoff = payload["handoff"]
        self.assertEqual(WORKSPACE_AXON_WATCH, handoff["source_workspace_id"])
        self.assertEqual("workspace_dashpro", handoff["target_workspace_id"])
        summary = payload["target_workspace_summary"]
        self.assertEqual("workspace_dashpro", summary["workspace_id"])
        self.assertEqual("project_path", summary["connection_kind"])
        self.assertTrue(str(summary.get("project_root", "")).endswith("dashpro"))

    def test_handoff_from_watch_to_local_returns_project_path_summary(self) -> None:
        response = self.client.post(
            f"/api/workspaces/{WORKSPACE_AXON_WATCH}/handoffs",
            json={
                "target_workspace_id": WORKSPACE_AXON_LOCAL,
                "task": "Cross-repo parity handoff",
                "reason": "P-D4 multi-project proof",
            },
        )
        self.assertEqual(200, response.status_code)
        payload = response.json()
        handoff = payload["handoff"]
        self.assertEqual(WORKSPACE_AXON_WATCH, handoff["source_workspace_id"])
        self.assertEqual(WORKSPACE_AXON_LOCAL, handoff["target_workspace_id"])
        self.assertEqual("recorded", handoff["status"])

        summary = payload["target_workspace_summary"]
        self.assertEqual(WORKSPACE_AXON_LOCAL, summary["workspace_id"])
        self.assertEqual("project_path", summary["connection_kind"])
        self.assertTrue(str(summary.get("project_root", "")).endswith("axon-local"))

    def test_multi_project_bindings_checker_passes(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/verify/check_multi_project_bindings.py"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, msg=result.stderr or result.stdout)


@unittest.skipUnless(_stack_available(), "dev stack not running on control-plane base URL")
@unittest.skipUnless(
    EXPECTED_AXON_LOCAL_ROOT.is_dir(),
    "sibling axon-local repo not present for default bindings",
)
class ParityD4MultiProjectLiveAcceptance(unittest.TestCase):
    def test_git_status_runs_in_bound_axon_watch_project(self) -> None:
        status, payload = _request(
            "POST",
            f"{CONTROL_PLANE_BASE}/api/chat/messages",
            {"workspace_id": WORKSPACE_AXON_WATCH, "content": "git status"},
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

    def test_live_handoff_from_watch_to_local(self) -> None:
        status, payload = _request(
            "POST",
            f"{CONTROL_PLANE_BASE}/api/workspaces/{WORKSPACE_AXON_WATCH}/handoffs",
            {
                "target_workspace_id": WORKSPACE_AXON_LOCAL,
                "task": "Live multi-project handoff",
                "reason": "P-D4 acceptance",
            },
        )
        self.assertEqual(200, status)
        self.assertIsInstance(payload, dict)
        handoff = payload.get("handoff")
        self.assertIsInstance(handoff, dict)
        assert isinstance(handoff, dict)
        self.assertEqual(WORKSPACE_AXON_WATCH, handoff.get("source_workspace_id"))
        self.assertEqual(WORKSPACE_AXON_LOCAL, handoff.get("target_workspace_id"))


if __name__ == "__main__":
    unittest.main()
