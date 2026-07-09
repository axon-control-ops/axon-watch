"""TEST-0 live acceptance against workspace_smoke on the dev stack.

Requires `./scripts/dev/up.sh` (ports 4173 / 8787 / 8788).

Run:
  python3 -m unittest tests.test_test0_workspace_smoke_acceptance
  ./scripts/verify/test0-workspace-smoke.sh
"""

from __future__ import annotations

import json
import os
import unittest
import urllib.error
import urllib.request
from pathlib import Path

WORKSPACE_ID = "workspace_smoke"
CONTROL_PLANE_BASE = os.environ.get(
    "AXON_WATCH_CONTROL_PLANE_BASE",
    "http://127.0.0.1:8787",
)
CONSOLE_WEB_BASE = os.environ.get(
    "AXON_WATCH_CONSOLE_WEB_BASE",
    "http://127.0.0.1:4173",
)
REPO_ROOT = Path(__file__).resolve().parents[1]


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


@unittest.skipUnless(_stack_available(), "dev stack not running on control-plane base URL")
class Test0WorkspaceSmokeAcceptance(unittest.TestCase):
    def test_briefing_notice_and_advise(self) -> None:
        status, payload = _request("GET", f"{CONTROL_PLANE_BASE}/api/briefing")
        self.assertEqual(200, status)
        self.assertIsInstance(payload, dict)
        self.assertTrue(str(payload.get("notice", "")).strip())
        self.assertTrue(str(payload.get("advise", "")).strip())

    def test_workspace_smoke_is_listed(self) -> None:
        status, payload = _request("GET", f"{CONTROL_PLANE_BASE}/api/workspaces")
        self.assertEqual(200, status)
        items = payload.get("items") if isinstance(payload, dict) else payload
        self.assertIsInstance(items, list)
        workspace_ids = [item["workspace_id"] for item in items]
        self.assertIn(WORKSPACE_ID, workspace_ids)

    def test_runtime_summary_ready(self) -> None:
        status, payload = _request("GET", f"{CONTROL_PLANE_BASE}/api/runtime/summary")
        self.assertEqual(200, status)
        self.assertIsInstance(payload, dict)
        self.assertTrue(payload.get("control_plane", {}).get("ready"))

    def test_attention_sidebar_surfaces(self) -> None:
        runs_status, runs_payload = _request("GET", f"{CONTROL_PLANE_BASE}/api/runs")
        self.assertEqual(200, runs_status)
        run_items = runs_payload.get("items") if isinstance(runs_payload, dict) else runs_payload
        self.assertIsInstance(run_items, list)

        inbox_status, inbox_payload = _request("GET", f"{CONTROL_PLANE_BASE}/api/inbox")
        self.assertEqual(200, inbox_status)
        self.assertIsInstance(inbox_payload, dict)

        briefing_status, briefing_payload = _request("GET", f"{CONTROL_PLANE_BASE}/api/briefing")
        self.assertEqual(200, briefing_status)
        self.assertIn("top_signals", briefing_payload)
        self.assertIn("pending_approvals", briefing_payload)

    def test_command_executor_git_status(self) -> None:
        status, payload = _request(
            "POST",
            f"{CONTROL_PLANE_BASE}/api/chat/messages",
            {"workspace_id": WORKSPACE_ID, "content": "git status"},
        )
        self.assertEqual(200, status)
        self.assertIsInstance(payload, dict)
        messages = payload.get("messages", [])
        agent_messages = [message for message in messages if message.get("role") == "agent"]
        self.assertTrue(agent_messages)
        agent_copy = agent_messages[-1]["content"].lower()
        self.assertNotIn("unsupported command", agent_copy)
        self.assertTrue("git" in agent_copy or "status" in agent_copy or "executed" in agent_copy)

    def test_command_executor_resume_from_review(self) -> None:
        status, payload = _request(
            "POST",
            f"{CONTROL_PLANE_BASE}/api/chat/messages",
            {"workspace_id": WORKSPACE_ID, "content": "resume from review"},
        )
        self.assertEqual(200, status)
        self.assertIsInstance(payload, dict)
        messages = payload.get("messages", [])
        agent_messages = [message for message in messages if message.get("role") == "agent"]
        self.assertTrue(agent_messages)
        agent_copy = agent_messages[-1]["content"].lower()
        self.assertNotIn("unsupported command", agent_copy)

    def test_mission_control_view_helpers_present(self) -> None:
        view_path = REPO_ROOT / "apps/console-web/src/lib/operator-status-radar-view.ts"
        panel_path = REPO_ROOT / "apps/console-web/src/components/shell/OperatorStatusRadarPanel.vue"
        self.assertTrue(view_path.is_file())
        self.assertTrue(panel_path.is_file())
        panel_source = panel_path.read_text(encoding="utf-8")
        self.assertIn("Mission Control", panel_source)
        self.assertIn("operatorExecutionStage", panel_source)
        self.assertIn("Open terminal", panel_source)

    def test_compact_layout_media_queries_present(self) -> None:
        shell_dir = REPO_ROOT / "apps/console-web/src/styles/shell"
        css_source = "".join(
            path.read_text(encoding="utf-8")
            for path in sorted(shell_dir.glob("mockup-shell-*.css"))
        )
        self.assertIn("@media (max-width: 1280px)", css_source)
        self.assertIn("@media (max-width: 960px)", css_source)

    def test_console_web_serves_shell(self) -> None:
        status, payload = _request("GET", f"{CONSOLE_WEB_BASE}/")
        self.assertEqual(200, status)
        self.assertIsInstance(payload, str)
        self.assertIn("<html", payload.lower())


if __name__ == "__main__":
    unittest.main()
