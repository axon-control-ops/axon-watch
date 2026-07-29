"""G3.6 agent orchestration parity — bounded IMPORT_MATRIX runtime workflows."""

from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from tests.support.control_plane_db import isolate_control_plane_db

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTROL_PLANE_ROOT = REPO_ROOT / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.cli_runtime.mcp_registry import mcp_tools_for_composer_mode  # noqa: E402
from app.cli_runtime.recovery import ordered_runtime_candidates  # noqa: E402
from app.cli_runtime.router import dispatch_ide_composer  # noqa: E402
from app.main import app  # noqa: E402
from app.persistence import run_store  # noqa: E402
from app.runs.service import get_run  # noqa: E402

# Bounded adopt/adapt rows from docs/planning/IMPORT_MATRIX.md § Runtime / AI Orchestration.
IMPORT_MATRIX_RUNTIME_OWNERS: dict[str, str] = {
    "Cursor CLI agent loop": "services/control-plane/app/cli_runtime/cursor_agent.py",
    "Claude Code CLI agent loop": "services/control-plane/app/cli_runtime/claude_agent.py",
    "Codex CLI agent loop": "services/control-plane/app/cli_runtime/codex_agent.py",
    "CLI binary catalog / resolve": "services/control-plane/app/cli_runtime/catalog.py",
    "Cursor -> Codex reroute / recovery": "services/control-plane/app/cli_runtime/recovery.py",
    "Model Context Protocol (MCP) integration": "services/control-plane/app/cli_runtime/mcp_registry.py",
}

# Cloud adapters are deferred; router returns an explicit unavailable message until modules land.
IMPORT_MATRIX_RUNTIME_DEFERRED: dict[str, str] = {
    "Cursor cloud agents / automations": "services/control-plane/app/cli_runtime/cloud_cursor.py",
    "Codex cloud tasks": "services/control-plane/app/cli_runtime/cloud_codex.py",
}


class ImportMatrixRuntimeOwnerTests(unittest.TestCase):
    def test_adapt_rows_map_to_bounded_modules(self) -> None:
        for capability, owner_path in IMPORT_MATRIX_RUNTIME_OWNERS.items():
            with self.subTest(capability=capability):
                self.assertTrue(
                    (REPO_ROOT / owner_path).is_file(),
                    msg=f"Missing bounded owner for {capability}: {owner_path}",
                )

    def test_cloud_runtime_adapters_are_explicitly_deferred(self) -> None:
        for capability, owner_path in IMPORT_MATRIX_RUNTIME_DEFERRED.items():
            with self.subTest(capability=capability):
                self.assertFalse(
                    (REPO_ROOT / owner_path).exists(),
                    msg=f"{capability} should remain deferred until {owner_path} lands",
                )

    def test_ollama_path_discarded_from_runtime_fabric(self) -> None:
        fabric = REPO_ROOT / "services/control-plane/app/cli_runtime"
        for path in fabric.rglob("*.py"):
            text = path.read_text(encoding="utf-8").lower()
            with self.subTest(path=str(path.relative_to(REPO_ROOT))):
                self.assertNotIn("ollama", text)


class RuntimeRecoveryParityTests(unittest.TestCase):
    def test_cursor_primary_then_codex_fallback_order(self) -> None:
        snapshot = {
            "default_runtime": "cursor_local",
            "local": [
                {"id": "cursor_local", "family": "cursor", "ready": True},
                {"id": "codex_local", "family": "codex", "ready": True},
            ],
            "cloud": [],
        }
        ordered = ordered_runtime_candidates(snapshot)
        ids = [str(record.get("id") or "") for record in ordered]
        self.assertEqual("cursor_local", ids[0])
        self.assertIn("codex_local", ids)


class AgentOrchestrationWorkflowParityTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)
        self.streaming_env = patch.dict(
            os.environ,
            {"AXON_WATCH_LANE_B_STREAMING": "0"},
            clear=False,
        )
        self.streaming_env.start()
        self.addCleanup(self.streaming_env.stop)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def test_default_verify_wiring_includes_agent_orchestration_parity(self) -> None:
        package = json.loads((REPO_ROOT / "package.json").read_text(encoding="utf-8"))
        verify_script = package["scripts"]["verify:agent-orchestration-parity"]
        gate_script = (REPO_ROOT / "scripts/verify/test20-agent-orchestration-parity.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("test20-agent-orchestration-parity.sh", verify_script)
        self.assertIn("tests.test_agent_orchestration_parity", gate_script)

    def test_dispatch_fallback_still_attaches_mode_filtered_mcp_tools(self) -> None:
        result = dispatch_ide_composer(
            workspace_id="workspace_missing",
            composer_mode="ask",
            user_prompt="Summarize README",
            context_block="ctx",
        )
        mcp_tools = result.get("mcp_tools")
        self.assertIsInstance(mcp_tools, dict)
        ask_ids = {item["id"] for item in mcp_tools.get("items", [])}
        self.assertIn("workspace_files.read", ask_ids)
        self.assertNotIn("runs.history", ask_ids)

    @patch(
        "app.chat.lane_b_post_message.generate_lane_b_result",
        return_value={
            "content": "Bounded agent reply\n\nConfidence: 8/10",
            "dispatched": True,
            "runtime_id": "cursor_local",
            "runtime_label": "Cursor CLI (local)",
            "reason": "",
            "execution_tier": "executing",
            "mcp_tools": mcp_tools_for_composer_mode("agent"),
        },
    )
    def test_ide_agent_workflow_persists_run_phase_not_transcript(self, _mock_lane_b) -> None:
        response = self.client.post(
            "/api/chat/messages",
            json={
                "workspace_id": "workspace_alpha",
                "content": "Implement the orchestration slice.",
                "composer_mode": "agent",
                "execution_access": "full",
            },
        )
        self.assertEqual(200, response.status_code)
        payload = response.json()
        run_id = str(payload["run_id"])
        self.assertTrue(run_id.startswith("run_"))

        persisted = get_run(run_id)
        self.assertEqual("completed", persisted["phase"])
        self.assertEqual("completed", payload["run"]["phase"])
        self.assertNotIn("completed", payload["messages"][2]["content"].lower())

    @patch(
        "app.chat.lane_b_post_message.generate_lane_b_result",
        return_value={
            "content": "Runtime-backed reply",
            "dispatched": True,
            "runtime_id": "cursor_local",
            "runtime_label": "Cursor CLI (local)",
            "reason": "",
            "mcp_tools": mcp_tools_for_composer_mode("agent"),
        },
    )
    def test_ide_agent_workflow_emits_contract_receipts(self, _mock_lane_b) -> None:
        response = self.client.post(
            "/api/chat/messages",
            json={
                "workspace_id": "workspace_alpha",
                "content": "Ship the donor workflow parity tests.",
                "composer_mode": "agent",
            },
        )
        self.assertEqual(200, response.status_code)
        run_id = str(response.json()["run_id"])

        history = self.client.get(f"/api/runs/{run_id}/history").json()["items"]
        receipt_types = [item["receipt"]["type"] for item in history]
        self.assertIn("runtime_dispatch", receipt_types)

    def test_mcp_tools_api_exposes_full_registry_for_composer_filtering(self) -> None:
        response = self.client.get("/api/runtime/mcp-tools")
        self.assertEqual(200, response.status_code)
        registry = response.json()
        self.assertGreaterEqual(registry["count"], 4)

        ask_tools = mcp_tools_for_composer_mode("ask")
        agent_tools = mcp_tools_for_composer_mode("agent")
        self.assertLess(ask_tools["count"], agent_tools["count"])
        ask_ids = {item["id"] for item in ask_tools["items"]}
        self.assertIn("workspace_files.read", ask_ids)
        self.assertNotIn("runs.history", ask_ids)


if __name__ == "__main__":
    unittest.main()
