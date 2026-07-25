"""Regression: vault state paths must resolve to the repo root, not services/."""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch


class VaultPathsTests(unittest.TestCase):
    def test_repo_root_is_axon_watch_repo_not_services(self) -> None:
        from app.vault.paths import repo_root

        root = repo_root()
        self.assertEqual(root.name, "axon-watch")
        self.assertTrue((root / "services" / "axon-watch").is_dir())
        self.assertNotEqual(root.name, "services")

    def test_relative_state_dir_does_not_land_under_services(self) -> None:
        from app.vault import paths as vault_paths

        with patch.dict("os.environ", {"AXON_WATCH_STATE_DIR": ".local/state"}, clear=False):
            state = vault_paths.state_dir()
        self.assertEqual(state, (vault_paths.repo_root() / ".local" / "state").resolve())
        self.assertNotIn("/services/.local/state", str(state))
        self.assertEqual(vault_paths.vault_db_path(), state / "vault.db")
        self.assertEqual(vault_paths.auto_unlock_keyfile_path(), state / ".vault_auto_unlock")


if __name__ == "__main__":
    unittest.main()
