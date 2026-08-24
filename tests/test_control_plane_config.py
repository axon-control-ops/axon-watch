"""Tests for shared control-plane config defaults."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "services" / "control-plane"))

from app.config import _cors_origins  # noqa: E402


class ControlPlaneConfigTests(unittest.TestCase):
    def test_default_cors_origins_include_local_web_dev_ports(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            origins = _cors_origins()

        self.assertIn("http://127.0.0.1:4173", origins)
        self.assertIn("http://localhost:4173", origins)
        self.assertIn("http://127.0.0.1:8081", origins)
        self.assertIn("http://localhost:8081", origins)
        self.assertIn("http://127.0.0.1:19006", origins)
        self.assertIn("http://localhost:19006", origins)

    def test_env_cors_origins_extend_default_local_origins(self) -> None:
        with patch.dict(
            os.environ,
            {"AXON_WATCH_CORS_ORIGINS": "https://axon.example, http://localhost:8081"},
            clear=True,
        ):
            origins = _cors_origins()

        self.assertIn("https://axon.example", origins)
        self.assertIn("http://127.0.0.1:4173", origins)
        self.assertIn("http://localhost:8081", origins)
        self.assertEqual(1, origins.count("http://localhost:8081"))


if __name__ == "__main__":
    unittest.main()
