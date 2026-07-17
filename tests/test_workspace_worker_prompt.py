from __future__ import annotations

import unittest

import sys
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.workspace_agents.config_loader import EmployeeConfig  # noqa: E402
from app.workspace_agents.worker_prompt import build_continuous_worker_prompt  # noqa: E402


class WorkspaceWorkerPromptTests(unittest.TestCase):
    def test_build_continuous_worker_prompt_includes_role_and_workspace(self) -> None:
        prompt = build_continuous_worker_prompt(
            workspace_id="workspace_axon_watch",
            employee=EmployeeConfig(
                name="Shell Craft",
                role="frontend",
                owns="Vue shell and IDE polish",
                schedule="continuous",
            ),
        )
        self.assertIn("workspace_axon_watch", prompt)
        self.assertIn("frontend", prompt)
        self.assertIn("Shell Craft", prompt)
        self.assertIn("Vue shell and IDE polish", prompt)


if __name__ == "__main__":
    unittest.main()
