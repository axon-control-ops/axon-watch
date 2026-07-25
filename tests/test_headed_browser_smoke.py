"""Tests for headed browser smoke helpers."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "verify"))

import headed_browser_smoke as smoke  # noqa: E402


class HeadedBrowserSmokeTests(unittest.TestCase):
    def test_console_base_url_default(self) -> None:
        with patch.dict("os.environ", {"AXON_WATCH_CONSOLE_WEB_PORT": "5173"}, clear=False):
            self.assertEqual(smoke._console_base_url(), "http://127.0.0.1:5173")

    def test_playwright_usable_false_when_import_missing(self) -> None:
        with patch.dict("sys.modules", {"playwright": None}):
            self.assertFalse(smoke._playwright_usable())

    def test_run_smoke_requires_playwright(self) -> None:
        with patch.object(smoke, "_health_ok"), patch.object(smoke, "_playwright_usable", return_value=False):
            with self.assertRaisesRegex(RuntimeError, "Playwright is unavailable"):
                smoke.run_smoke(console_base_url="http://127.0.0.1:4173")


if __name__ == "__main__":
    unittest.main()
