"""Unit tests for control-plane ↔ watch import isolation helpers."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from tests.support.watch_app_loader import (  # noqa: E402
    load_control_plane_watch_pair,
    restore_app_modules,
    snapshot_app_modules,
)


class WatchAppLoaderTests(unittest.TestCase):
    def test_load_control_plane_watch_pair_restores_control_plane_modules(self) -> None:
        from app.main import app as control_plane_app  # noqa: WPS433

        wrapped, control_plane_modules = load_control_plane_watch_pair()
        self.addCleanup(lambda: restore_app_modules(control_plane_modules))

        # Control-plane imports are active again for TestClient-style callers.
        self.assertIn("app.main", sys.modules)
        self.assertIs(sys.modules["app.main"].app, control_plane_app)

        # Wrapped ASGI is callable (module swap happens per request).
        self.assertTrue(callable(wrapped))

        # Snapshot captures the restored control-plane tree, not watch modules.
        current = snapshot_app_modules()
        self.assertIn("app.main", current)
        self.assertIs(current["app.main"].app, control_plane_app)


if __name__ == "__main__":
    unittest.main()
