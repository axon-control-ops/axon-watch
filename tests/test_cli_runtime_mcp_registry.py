from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.cli_runtime.mcp_registry import (  # noqa: E402
    mcp_tools_for_composer_mode,
    runtime_mcp_tools_registry,
)


class CliRuntimeMcpRegistryTests(unittest.TestCase):
    def test_runtime_registry_lists_bounded_tools(self) -> None:
        payload = runtime_mcp_tools_registry()
        self.assertGreaterEqual(payload["count"], 3)
        items = payload["items"]
        self.assertTrue(any(item["id"] == "workspace_files.read" for item in items))

    def test_mcp_tools_for_composer_mode_filters_mode_support(self) -> None:
        ask_tools = mcp_tools_for_composer_mode("ask")
        plan_tools = mcp_tools_for_composer_mode("plan")
        debug_tools = mcp_tools_for_composer_mode("debug")
        self.assertGreater(ask_tools["count"], 0)
        self.assertGreater(plan_tools["count"], 0)
        self.assertGreater(debug_tools["count"], 0)
        ask_ids = {item["id"] for item in ask_tools["items"]}
        plan_ids = {item["id"] for item in plan_tools["items"]}
        debug_ids = {item["id"] for item in debug_tools["items"]}
        self.assertIn("workspace_files.read", ask_ids)
        self.assertIn("runs.history", plan_ids)
        self.assertNotIn("runs.history", ask_ids)
        self.assertIn("workspace_files.read", debug_ids)
        self.assertIn("runs.history", debug_ids)


if __name__ == "__main__":
    unittest.main()
