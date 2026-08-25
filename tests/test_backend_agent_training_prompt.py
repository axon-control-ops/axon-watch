from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.workspace_agents.config_loader import EmployeeConfig  # noqa: E402
from app.workspace_agents.worker_prompt import build_continuous_worker_prompt  # noqa: E402


class BackendAgentTrainingPromptTests(unittest.TestCase):
    def test_backend_prompt_teaches_verified_sources_and_learning_loop(self) -> None:
        with patch(
            "app.workspace_agents.worker_prompt.build_team_roster_context",
            return_value="",
        ):
            prompt = build_continuous_worker_prompt(
                workspace_id="workspace_young_eagles_day_care",
                employee=EmployeeConfig(
                    name="Marco",
                    role="backend",
                    owns="Database, API, and migration safety",
                    schedule="continuous",
                ),
                task={
                    "task_id": "task-backend-docs",
                    "goal": "Fix a migration lint failure and document the safe recovery path.",
                },
            )
        self.assertIn("Backend agent operating model", prompt)
        self.assertIn("official documentation", prompt)
        self.assertIn("primary/verified source", prompt)
        self.assertIn("check Vault/env readiness without printing secrets", prompt)
        self.assertIn("add or update a small doc, test, prompt clause, or self-heal helper", prompt)


if __name__ == "__main__":
    unittest.main()
