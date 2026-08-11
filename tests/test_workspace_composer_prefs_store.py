from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.persistence.workspace_composer_prefs_store import (  # noqa: E402
    get_workspace_composer_prefs,
    resolve_worker_runtime_model,
    resolve_worker_runtime_target,
    set_workspace_composer_prefs,
)
from app.persistence import operator_presence_settings_store  # noqa: E402


class WorkspaceComposerPrefsStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._db = Path(self._tmp.name) / "control-plane.sqlite3"
        self._prev = os.environ.get("AXON_WATCH_CONTROL_PLANE_DB")
        os.environ["AXON_WATCH_CONTROL_PLANE_DB"] = str(self._db)

    def tearDown(self) -> None:
        if self._prev is None:
            os.environ.pop("AXON_WATCH_CONTROL_PLANE_DB", None)
        else:
            os.environ["AXON_WATCH_CONTROL_PLANE_DB"] = self._prev
        self._tmp.cleanup()

    def test_defaults_to_auto_for_workers(self) -> None:
        prefs = get_workspace_composer_prefs("workspace_axon_watch")
        self.assertEqual(prefs["cursor_cli_model"], "auto")
        self.assertIsNone(resolve_worker_runtime_model("workspace_axon_watch"))

    def test_composer_pin_passes_through(self) -> None:
        set_workspace_composer_prefs(
            "workspace_axon_watch",
            cursor_cli_model="composer-2.5-fast",
        )
        self.assertEqual(
            resolve_worker_runtime_model("workspace_axon_watch"),
            "composer-2.5-fast",
        )

    def test_explicit_api_pin_passes_through(self) -> None:
        set_workspace_composer_prefs(
            "workspace_axon_watch",
            cursor_cli_model="gpt-5.4-high",
        )
        self.assertEqual(
            resolve_worker_runtime_model("workspace_axon_watch"),
            "gpt-5.4-high",
        )

    def test_explicit_workspace_runtime_target_wins_over_full_auto_default(self) -> None:
        set_workspace_composer_prefs(
            "workspace_axon_watch",
            runtime_target="cursor_local",
        )
        operator_presence_settings_store.save_settings(
            {
                "autonomy_mode": "full",
                "auto_composer_runtime_override_enabled": True,
                "auto_composer_runtime_target": "claude_local",
            }
        )

        self.assertEqual(
            resolve_worker_runtime_target("workspace_axon_watch"),
            "cursor_local",
        )

    def test_full_auto_runtime_override_is_used_when_no_runtime_is_selected(self) -> None:
        operator_presence_settings_store.save_settings(
            {
                "autonomy_mode": "full",
                "auto_composer_runtime_override_enabled": True,
                "auto_composer_runtime_target": "claude_local",
            }
        )
        self.assertEqual(
            resolve_worker_runtime_target("workspace_axon_watch"),
            "claude_local",
        )

    def test_disabled_auto_runtime_override_restores_workspace_runtime_target(self) -> None:
        set_workspace_composer_prefs(
            "workspace_axon_watch",
            runtime_target="cursor_local",
        )
        operator_presence_settings_store.save_settings(
            {
                "autonomy_mode": "semi",
                "auto_composer_runtime_override_enabled": True,
                "auto_composer_runtime_target": "claude_local",
            }
        )

        self.assertEqual(
            resolve_worker_runtime_target("workspace_axon_watch"),
            "cursor_local",
        )


if __name__ == "__main__":
    unittest.main()
