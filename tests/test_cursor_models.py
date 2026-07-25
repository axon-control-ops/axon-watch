from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.cli_runtime import cursor_models  # noqa: E402


class CursorModelsTests(unittest.TestCase):
    def test_list_cursor_models_parses_available_models_output(self) -> None:
        proc = type(
            "Proc",
            (),
            {
                "returncode": 0,
                "stdout": "Available models\ncomposer-2.5 - Composer 2.5\ngpt-5.4 - GPT 5.4\n",
                "stderr": "",
            },
        )()
        with patch("app.cli_runtime.cursor_models._run_command", return_value=proc):
            models = cursor_models.list_cursor_models("/usr/bin/cursor")
        self.assertEqual(
            [
                {"id": "composer-2.5", "label": "Composer 2.5", "description": "Composer 2.5"},
                {"id": "gpt-5.4", "label": "GPT 5.4", "description": "GPT 5.4"},
            ],
            models,
        )

    @patch("app.cli_runtime.cursor_models.fetch_runtime_context")
    @patch("app.cli_runtime.cursor_models.find_cursor_cli", return_value="/usr/bin/cursor")
    @patch("app.cli_runtime.cursor_models.list_cursor_models")
    @patch("app.cli_runtime.cursor_models._cursor_auth_status")
    def test_cursor_runtime_snapshot_prefers_live_catalog(
        self,
        mock_auth,
        mock_list_models,
        _find_cursor,
        mock_fetch_context,
    ) -> None:
        mock_fetch_context.return_value = {"vault_runtime": {"unlocked": False}, "env": {}}
        mock_auth.return_value = {"logged_in": True, "message": "ready"}
        mock_list_models.return_value = [
            {"id": "composer-2.5", "label": "Composer 2.5", "description": "Composer 2.5"},
        ]
        snapshot = cursor_models.cursor_runtime_snapshot(force_refresh=True)
        self.assertTrue(snapshot["installed"])
        self.assertEqual("live", snapshot["catalog_source"])
        self.assertEqual(1, len(snapshot["available_models"]))


if __name__ == "__main__":
    unittest.main()
