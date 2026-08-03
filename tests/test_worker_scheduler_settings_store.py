"""Worker scheduler settings store persistence tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.persistence import run_store, worker_scheduler_settings_store  # noqa: E402


class WorkerSchedulerSettingsStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)

    def test_load_settings_defaults_off(self) -> None:
        settings = worker_scheduler_settings_store.load_settings()
        self.assertFalse(settings["scheduler_enabled"])
        self.assertEqual(1, settings["max_active"])
        self.assertEqual(1, settings["max_starts_per_tick"])
        self.assertEqual({}, settings["employee_enabled"])

    def test_patch_settings_persists_scheduler_toggle(self) -> None:
        saved = worker_scheduler_settings_store.patch_settings({"scheduler_enabled": True})
        self.assertTrue(saved["scheduler_enabled"])
        self.assertIn("updated_at", saved)

        reloaded = worker_scheduler_settings_store.load_settings()
        self.assertTrue(reloaded["scheduler_enabled"])
        self.assertEqual(saved["updated_at"], reloaded["updated_at"])

    def test_patch_settings_clamps_numeric_bounds(self) -> None:
        saved = worker_scheduler_settings_store.patch_settings(
            {
                "max_active": 999,
                "max_starts_per_tick": 0,
            }
        )
        self.assertEqual(16, saved["max_active"])
        self.assertEqual(1, saved["max_starts_per_tick"])

    def test_patch_settings_merges_employee_enabled_overlay(self) -> None:
        worker_scheduler_settings_store.patch_settings(
            {"employee_enabled": {"workspace_a:frontend": False}}
        )
        saved = worker_scheduler_settings_store.patch_settings(
            {"employee_enabled": {"workspace_b:backend": False}}
        )
        self.assertEqual(
            {
                "workspace_a:frontend": False,
                "workspace_b:backend": False,
            },
            saved["employee_enabled"],
        )

    def test_is_employee_enabled_respects_file_and_overlay(self) -> None:
        self.assertTrue(
            worker_scheduler_settings_store.is_employee_enabled(
                "workspace_demo",
                "backend",
                file_enabled=True,
            )
        )
        self.assertFalse(
            worker_scheduler_settings_store.is_employee_enabled(
                "workspace_demo",
                "backend",
                file_enabled=False,
            )
        )
        worker_scheduler_settings_store.patch_settings(
            {"employee_enabled": {"workspace_demo:backend": False}}
        )
        self.assertFalse(
            worker_scheduler_settings_store.is_employee_enabled(
                "workspace_demo",
                "backend",
                file_enabled=True,
            )
        )

    def test_reset_store_clears_persisted_overlay(self) -> None:
        worker_scheduler_settings_store.patch_settings({"scheduler_enabled": True})
        worker_scheduler_settings_store.reset_store()
        settings = worker_scheduler_settings_store.load_settings()
        self.assertFalse(settings["scheduler_enabled"])
        self.assertEqual({}, settings["employee_enabled"])

    def test_workspace_enabled_defaults_true_and_pauses_all_workspace_roles(self) -> None:
        self.assertTrue(worker_scheduler_settings_store.is_workspace_enabled("workspace_dashpro"))
        worker_scheduler_settings_store.patch_settings(
            {"workspace_enabled": {"workspace_bkk_invoice_system": False}}
        )
        self.assertFalse(
            worker_scheduler_settings_store.is_workspace_enabled(
                "workspace_bkk_invoice_system"
            )
        )
        self.assertFalse(
            worker_scheduler_settings_store.is_employee_enabled(
                "workspace_bkk_invoice_system", "watcher", file_enabled=True
            )
        )
        self.assertTrue(
            worker_scheduler_settings_store.is_employee_enabled(
                "workspace_dashpro", "watcher", file_enabled=True
            )
        )


if __name__ == "__main__":
    unittest.main()
