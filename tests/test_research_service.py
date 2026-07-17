from __future__ import annotations

import os
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


class RepoEnvFileTests(unittest.TestCase):
    def test_loads_missing_keys_from_env_file(self) -> None:
        from app.research import env_file as env_file_mod

        with patch.object(env_file_mod, "_LOADED", False), patch.dict(
            os.environ, {"AXON_WATCH_GOOGLE_CSE_API_KEY": "", "AXON_WATCH_GOOGLE_CSE_CX": ""}, clear=False
        ):
            os.environ.pop("AXON_WATCH_GOOGLE_CSE_API_KEY", None)
            os.environ.pop("AXON_WATCH_GOOGLE_CSE_CX", None)
            tmp = Path(self.id().replace(".", "_") + "_env")
            # Use a temp file via patched repo root
            import tempfile

            with tempfile.TemporaryDirectory() as td:
                root = Path(td)
                (root / ".env").write_text(
                    "AXON_WATCH_GOOGLE_CSE_API_KEY=from-file-key\n"
                    "AXON_WATCH_GOOGLE_CSE_CX=from-file-cx\n",
                    encoding="utf-8",
                )
                with patch.object(env_file_mod, "_repo_root", return_value=root):
                    env_file_mod.load_repo_env_file(force=True)
                self.assertEqual("from-file-key", os.environ.get("AXON_WATCH_GOOGLE_CSE_API_KEY"))
                self.assertEqual("from-file-cx", os.environ.get("AXON_WATCH_GOOGLE_CSE_CX"))

    def test_does_not_override_existing_env(self) -> None:
        from app.research import env_file as env_file_mod

        import tempfile

        with patch.object(env_file_mod, "_LOADED", False), patch.dict(
            os.environ,
            {
                "AXON_WATCH_GOOGLE_CSE_API_KEY": "already",
                "AXON_WATCH_GOOGLE_CSE_CX": "set",
            },
            clear=False,
        ), tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".env").write_text(
                "AXON_WATCH_GOOGLE_CSE_API_KEY=from-file\nAXON_WATCH_GOOGLE_CSE_CX=from-file\n",
                encoding="utf-8",
            )
            with patch.object(env_file_mod, "_repo_root", return_value=root):
                env_file_mod.load_repo_env_file(force=True)
            self.assertEqual("already", os.environ.get("AXON_WATCH_GOOGLE_CSE_API_KEY"))
            self.assertEqual("set", os.environ.get("AXON_WATCH_GOOGLE_CSE_CX"))


class GoogleCseProviderTests(unittest.TestCase):
    def test_prefers_google_cse_when_configured(self) -> None:
        from app.research import search as search_mod

        with patch.object(search_mod, "searxng_base_url", return_value=""), patch.dict(
            os.environ,
            {
                "AXON_WATCH_GOOGLE_CSE_API_KEY": "test-key",
                "AXON_WATCH_GOOGLE_CSE_CX": "test-cx",
                "AXON_WATCH_SEARXNG_URL": "",
            },
            clear=False,
        ), patch.object(
            search_mod,
            "_google_cse_search",
            return_value=[
                {
                    "title": "Vite",
                    "url": "https://vitejs.dev/",
                    "snippet": "Next Generation Frontend Tooling",
                }
            ],
        ) as mock_google, patch.object(
            search_mod,
            "_duckduckgo_instant_search",
            side_effect=AssertionError("ddg should not run"),
        ):
            payload = search_mod.search_web("vite")
        self.assertEqual("google_cse", payload["provider"])
        self.assertEqual(1, payload["count"])
        mock_google.assert_called_once_with("vite")

    def test_reads_dashpro_env_aliases(self) -> None:
        from app.research.search import google_cse_credentials

        with patch.dict(
            os.environ,
            {
                "AXON_WATCH_GOOGLE_CSE_API_KEY": "",
                "AXON_WATCH_GOOGLE_CSE_CX": "",
                "GOOGLE_SEARCH_API_KEY": "dash-key",
                "GOOGLE_CSE_ID": "dash-cx",
            },
            clear=False,
        ):
            self.assertEqual(("dash-key", "dash-cx"), google_cse_credentials())

    def test_reads_google_cse_from_unlocked_vault(self) -> None:
        from app.research.search import google_cse_credentials

        with patch.dict(os.environ, {}, clear=True), patch(
            "app.research.search._vault_env",
            return_value={
                "AXON_WATCH_GOOGLE_CSE_API_KEY": "vault-key",
                "AXON_WATCH_GOOGLE_CSE_CX": "vault-cx",
            },
        ):
            self.assertEqual(("vault-key", "vault-cx"), google_cse_credentials())

    def test_prefers_searxng_when_configured(self) -> None:
        from app.research import search as search_mod

        with patch.dict(
            os.environ,
            {
                "AXON_WATCH_SEARXNG_URL": "http://127.0.0.1:8080",
                "AXON_WATCH_GOOGLE_CSE_API_KEY": "test-key",
                "AXON_WATCH_GOOGLE_CSE_CX": "test-cx",
            },
            clear=False,
        ), patch.object(
            search_mod,
            "_searxng_search",
            return_value=[
                {"title": "FastAPI", "url": "https://fastapi.tiangolo.com/", "snippet": "docs"},
            ],
        ) as mock_searx, patch.object(
            search_mod,
            "_google_cse_search",
            side_effect=AssertionError("google should not run when searxng succeeds"),
        ):
            payload = search_mod.search_web("fastapi")
        self.assertEqual("searxng", payload["provider"])
        self.assertEqual(1, payload["count"])
        mock_searx.assert_called_once_with("fastapi")

    def test_falls_back_when_google_cse_errors(self) -> None:
        from app.research import search as search_mod

        with patch.object(search_mod, "searxng_base_url", return_value=""), patch.dict(
            os.environ,
            {
                "AXON_WATCH_GOOGLE_CSE_API_KEY": "test-key",
                "AXON_WATCH_GOOGLE_CSE_CX": "test-cx",
            },
            clear=False,
        ), patch.object(
            search_mod,
            "_google_cse_search",
            side_effect=ValueError("Google CSE error 403: disabled"),
        ), patch.object(
            search_mod,
            "_duckduckgo_instant_search",
            return_value=[
                {"title": "Fallback", "url": "https://example.com/", "snippet": "ok"}
            ],
        ):
            payload = search_mod.search_web("vite")
        self.assertEqual("duckduckgo_instant", payload["provider"])
        self.assertIn("403", str(payload.get("fallback_from") or ""))
        self.assertEqual(1, payload["count"])


if __name__ == "__main__":
    unittest.main()
