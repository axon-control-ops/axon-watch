from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.cli_runtime import codex_models  # noqa: E402


class CodexModelsTests(unittest.TestCase):
    def setUp(self) -> None:
        codex_models._MODEL_CACHE.clear()

    def test_list_codex_models_keeps_only_visible_catalog_entries(self) -> None:
        proc = type(
            "Proc",
            (),
            {
                "returncode": 0,
                "stdout": (
                    '{"models": ['
                    '{"slug":"gpt-5.5","display_name":"GPT-5.5",'
                    '"description":"Frontier coding model.",'
                    '"default_reasoning_level":"medium",'
                    '"supported_reasoning_levels":[{"effort":"low"},{"effort":"medium"},{"effort":"high"}],'
                    '"visibility":"list"},'
                    '{"slug":"hidden","visibility":"hidden"}'
                    ']}'
                ),
                "stderr": "",
            },
        )()
        with patch("app.cli_runtime.codex_models._run_command", return_value=proc):
            models = codex_models.list_codex_models("/usr/bin/codex")
        self.assertEqual(
            [{
                "id": "gpt-5.5",
                "label": "GPT-5.5",
                "description": "Frontier coding model.",
                "badge": "Medium",
                "default_reasoning_level": "medium",
                "reasoning_levels": ["low", "medium", "high"],
            }],
            models,
        )

    @patch("app.cli_runtime.codex_models.fetch_runtime_context")
    @patch("app.cli_runtime.codex_models.find_codex_cli", return_value="/usr/bin/codex")
    @patch("app.cli_runtime.codex_models.list_codex_models")
    @patch("app.cli_runtime.codex_models._codex_auth_status")
    def test_codex_runtime_snapshot_prefers_live_account_catalog(
        self,
        mock_auth,
        mock_list_models,
        _find_codex,
        mock_fetch_context,
    ) -> None:
        mock_fetch_context.return_value = {"vault_runtime": {"unlocked": False}, "env": {}}
        mock_auth.return_value = {"logged_in": True, "auth_method": "chatgpt", "message": "ready"}
        mock_list_models.return_value = [
            {"id": "gpt-5.5", "label": "GPT-5.5", "description": "Frontier coding model."},
        ]
        snapshot = codex_models.codex_runtime_snapshot(force_refresh=True)
        self.assertTrue(snapshot["installed"])
        self.assertEqual("live", snapshot["catalog_source"])
        self.assertEqual("gpt-5.5", snapshot["available_models"][0]["id"])


if __name__ == "__main__":
    unittest.main()
