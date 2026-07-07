from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.research.policy import validate_url  # noqa: E402
from app.research.service import search_web  # noqa: E402


class ResearchPolicyTests(unittest.TestCase):
    def test_blocks_localhost_urls(self) -> None:
        with self.assertRaises(ValueError):
            validate_url("http://localhost/docs")

    def test_blocks_private_ip_literals(self) -> None:
        with self.assertRaises(ValueError):
            validate_url("http://127.0.0.1/")

    def test_allows_public_https_url(self) -> None:
        url, host = validate_url("https://example.com/docs")
        self.assertEqual("example.com", host)
        self.assertTrue(url.startswith("https://example.com"))


class ResearchServiceTests(unittest.TestCase):
    @patch("app.research.service._search_web")
    def test_search_web_records_success(self, mock_search) -> None:
        mock_search.return_value = {
            "query": "vite",
            "provider": "duckduckgo_instant",
            "results": [{"title": "Vite", "url": "https://vitejs.dev/", "snippet": "docs"}],
            "count": 1,
        }
        payload = search_web("vite")
        self.assertTrue(payload.get("success"))
        self.assertEqual(1, payload.get("count"))


if __name__ == "__main__":
    unittest.main()
