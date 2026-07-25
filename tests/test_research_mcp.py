from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.cli_runtime.research_mcp import (  # noqa: E402
    _control_plane_root,
    ensure_workspace_research_mcp,
)


class ResearchMcpBootstrapTests(unittest.TestCase):
    def test_control_plane_root_points_at_package_root(self) -> None:
        root = _control_plane_root()
        self.assertEqual(root, CONTROL_PLANE_ROOT.resolve())
        self.assertTrue((root / "app" / "research" / "mcp_server.py").is_file())

    def test_ensure_workspace_research_mcp_writes_launchable_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            self.assertTrue(ensure_workspace_research_mcp(workspace_root))

            config_path = workspace_root / ".cursor" / "mcp.json"
            payload = json.loads(config_path.read_text(encoding="utf-8"))
            server = payload["mcpServers"]["axon-research"]

            self.assertEqual(str(CONTROL_PLANE_ROOT.resolve()), server["cwd"])
            self.assertEqual(
                str(CONTROL_PLANE_ROOT.resolve()),
                server["env"]["PYTHONPATH"],
            )
            self.assertEqual(["-m", "app.research.mcp_server"], server["args"])


if __name__ == "__main__":
    unittest.main()
