"""Unit tests for shared GitHub API probe header helpers."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

WATCH_SERVICE_ROOT = Path(__file__).resolve().parents[1] / "services" / "axon-watch"
_WATCH_PATH = str(WATCH_SERVICE_ROOT)


class GitHubProbeHeadersTests(unittest.TestCase):
    def setUp(self) -> None:
        self._saved_modules = {
            name: module
            for name, module in sys.modules.items()
            if name == "app" or name.startswith("app.")
        }
        for name in self._saved_modules:
            del sys.modules[name]
        while _WATCH_PATH in sys.path:
            sys.path.remove(_WATCH_PATH)
        sys.path.insert(0, _WATCH_PATH)
        import app.monitors.github_probe_headers as github_probe_headers  # noqa: WPS433

        self.mod = github_probe_headers

    def tearDown(self) -> None:
        for name in list(sys.modules):
            if name == "app" or name.startswith("app."):
                del sys.modules[name]
        while _WATCH_PATH in sys.path:
            sys.path.remove(_WATCH_PATH)
        sys.modules.update(self._saved_modules)

    def test_is_github_api_url(self) -> None:
        self.assertTrue(self.mod.is_github_api_url("https://api.github.com/zen"))
        self.assertFalse(self.mod.is_github_api_url("https://github.com/zen"))

    def test_headers_include_token_when_present(self) -> None:
        headers = self.mod.github_api_headers({"GITHUB_TOKEN": "ghs_demo"})
        self.assertEqual("Bearer ghs_demo", headers.get("Authorization"))
        self.assertEqual("application/vnd.github+json", headers.get("Accept"))

    def test_resolve_skips_placeholder_for_real_vault_token(self) -> None:
        token = self.mod.resolve_github_token(
            {
                "GITHUB_TOKEN": "__REPLACE__",
                "GH_TOKEN": "gho_real_token_from_vault_xxxxxxxx",
            }
        )
        self.assertEqual("gho_real_token_from_vault_xxxxxxxx", token)
        headers = self.mod.github_api_headers(
            {
                "GITHUB_TOKEN": "__REPLACE__",
                "GH_TOKEN": "gho_real_token_from_vault_xxxxxxxx",
            }
        )
        self.assertEqual(
            "Bearer gho_real_token_from_vault_xxxxxxxx",
            headers.get("Authorization"),
        )

    def test_looks_like_github_rate_limit(self) -> None:
        self.assertTrue(
            self.mod.looks_like_github_rate_limit(
                status_code=403,
                body='{"message":"API rate limit exceeded"}',
                headers={"X-RateLimit-Remaining": "0"},
            )
        )
        self.assertFalse(
            self.mod.looks_like_github_rate_limit(
                status_code=403,
                body='{"message":"Bad credentials"}',
                headers={"X-RateLimit-Remaining": "60"},
            )
        )


if __name__ == "__main__":
    unittest.main()
