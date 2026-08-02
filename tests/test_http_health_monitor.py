"""HTTP health monitor probe unit tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

WATCH_SERVICE_ROOT = Path(__file__).resolve().parents[1] / "services" / "axon-watch"
_WATCH_PATH = str(WATCH_SERVICE_ROOT)


class HttpHealthMonitorTests(unittest.TestCase):
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
        import app.monitors.http_health as http_health  # noqa: WPS433
        import app.monitors.monitor_probe as monitor_probe  # noqa: WPS433

        self.http_health = http_health
        self.monitor_probe = monitor_probe

    def tearDown(self) -> None:
        for name in list(sys.modules):
            if name == "app" or name.startswith("app."):
                del sys.modules[name]
        while _WATCH_PATH in sys.path:
            sys.path.remove(_WATCH_PATH)
        sys.modules.update(self._saved_modules)

    def test_unresolved_placeholder_skipped(self) -> None:
        status, detail = self.http_health.check_http_health(
            url="${AXON_WATCH_PUBLIC_BASE_URL}/api/health"
        )
        self.assertEqual("skipped", status)
        self.assertIn("unresolved", detail)

    def test_missing_url_skipped(self) -> None:
        status, detail = self.http_health.check_http_health(url="")
        self.assertEqual("skipped", status)
        self.assertIn("url missing", detail)

    def test_ok_status(self) -> None:
        response = MagicMock()
        response.status = 200
        response.read.return_value = b'{"status":"ok"}'
        response.__enter__.return_value = response
        response.__exit__.return_value = False
        with patch.object(self.http_health, "urlopen", return_value=response):
            status, detail = self.http_health.check_http_health(
                url="https://example.test/health",
                expect_json_status="ok",
            )
        self.assertEqual("ok", status)
        self.assertIn("reachable", detail)

    def test_github_rate_limit_is_warning_not_outage(self) -> None:
        from io import BytesIO
        from urllib.error import HTTPError

        body = b'{"message":"API rate limit exceeded for 1.2.3.4."}'
        raised = HTTPError(
            "https://api.github.com/zen",
            403,
            "Forbidden",
            hdrs={"X-RateLimit-Remaining": "0"},
            fp=BytesIO(body),
        )
        with patch.object(self.http_health, "urlopen", side_effect=raised):
            status, detail = self.http_health.check_http_health(
                url="https://api.github.com/zen",
            )
        self.assertEqual("warning", status)
        self.assertIn("rate limit", detail.lower())
        self.assertIn("not an outage", detail.lower())

    def test_github_bare_403_is_config_gap_not_outage(self) -> None:
        from io import BytesIO
        from urllib.error import HTTPError

        raised = HTTPError(
            "https://api.github.com/zen",
            403,
            "Forbidden",
            hdrs={"X-RateLimit-Remaining": "12"},
            fp=BytesIO(b'{"message":"Forbidden"}'),
        )
        with patch.object(self.http_health, "urlopen", side_effect=raised):
            status, detail = self.http_health.check_http_health(
                url="https://api.github.com/zen",
            )
        self.assertEqual("warning", status)
        self.assertIn("missing probe token", detail.lower())
        self.assertIn("not a github outage", detail.lower())

    def test_github_401_is_config_gap_not_outage(self) -> None:
        from io import BytesIO
        from urllib.error import HTTPError

        raised = HTTPError(
            "https://api.github.com/zen",
            401,
            "Unauthorized",
            hdrs={},
            fp=BytesIO(b'{"message":"Bad credentials"}'),
        )
        with patch.object(self.http_health, "urlopen", side_effect=raised):
            status, detail = self.http_health.check_http_health(
                url="https://api.github.com/zen",
            )
        self.assertEqual("warning", status)
        self.assertIn("placeholder probe token", detail.lower())
        self.assertIn("not a github outage", detail.lower())

    def test_transient_dns_retries_then_ok(self) -> None:
        from urllib.error import URLError

        response = MagicMock()
        response.status = 200
        response.read.return_value = b"Keep it logically awesome."
        response.headers = {}
        response.__enter__.return_value = response
        response.__exit__.return_value = False
        calls = {"n": 0}

        def fake_urlopen(*_args, **_kwargs):
            calls["n"] += 1
            if calls["n"] == 1:
                raise URLError("[Errno -3] Temporary failure in name resolution")
            return response

        with patch.object(self.http_health, "urlopen", side_effect=fake_urlopen):
            with patch.object(self.http_health.time, "sleep", return_value=None):
                status, detail = self.http_health.check_http_health(
                    url="https://api.github.com/zen",
                    retries=1,
                )
        self.assertEqual(2, calls["n"])
        self.assertEqual("ok", status)
        self.assertIn("reachable", detail)

    def test_transient_dns_exhausted_is_warning_not_critical(self) -> None:
        from urllib.error import URLError

        raised = URLError("[Errno -3] Temporary failure in name resolution")
        with patch.object(self.http_health, "urlopen", side_effect=raised):
            with patch.object(self.http_health.time, "sleep", return_value=None):
                status, detail = self.http_health.check_http_health(
                    url="https://api.github.com/zen",
                    retries=1,
                )
        self.assertEqual("warning", status)
        self.assertIn("dns temporarily failed", detail.lower())
        self.assertIn("local name resolution", detail.lower())
        self.assertNotIn("HTTP health probe failed:", detail)

    def test_non_dns_urlerror_remains_critical(self) -> None:
        from urllib.error import URLError

        raised = URLError("Connection refused")
        with patch.object(self.http_health, "urlopen", side_effect=raised):
            status, detail = self.http_health.check_http_health(
                url="https://api.github.com/zen",
                retries=1,
            )
        self.assertEqual("critical", status)
        self.assertIn("HTTP health probe failed:", detail)

    def test_probe_slice_injects_github_auth_header(self) -> None:
        captured: dict[str, object] = {}

        def _fake_check(**kwargs):
            captured.update(kwargs)
            return ("ok", "reachable (200)")

        with patch.object(self.monitor_probe, "check_http_health", side_effect=_fake_check):
            with patch.dict("os.environ", {"GH_TOKEN": "ghp_test_token"}, clear=False):
                records = self.monitor_probe.probe_monitor_slice(
                    {
                        "enabled": True,
                        "workspace_id": "workspace_axon_watch",
                        "workspace_label": "Axon-X",
                        "checks": [
                            {
                                "id": "github",
                                "type": "http_health",
                                "service": "GitHub API",
                                "url": "https://api.github.com/zen",
                                "bearer_token_env": "GH_TOKEN",
                            }
                        ],
                    }
                )
        self.assertEqual(1, len(records))
        self.assertEqual("ok", records[0]["status"])
        headers = captured.get("headers") or {}
        self.assertEqual("Bearer ghp_test_token", headers.get("Authorization"))
        self.assertIn("application/vnd.github+json", str(headers.get("Accept", "")))

    def test_probe_slice_http_health_only_without_project_root(self) -> None:
        with patch.object(
            self.monitor_probe,
            "check_http_health",
            return_value=("ok", "reachable (200)"),
        ):
            records = self.monitor_probe.probe_monitor_slice(
                {
                    "enabled": True,
                    "workspace_id": "workspace_axon_watch",
                    "workspace_label": "Axon-X",
                    "checks": [
                        {
                            "id": "public_health",
                            "type": "http_health",
                            "service": "Public origin",
                            "url": "https://axon.example/api/health",
                        }
                    ],
                }
            )
        self.assertEqual(1, len(records))
        self.assertEqual("http_health", records[0]["check_type"])
        self.assertEqual("ok", records[0]["status"])

    def test_github_rate_limit_without_token_adds_vault_hint(self) -> None:
        with patch.object(
            self.monitor_probe,
            "check_http_health",
            return_value=(
                "warning",
                (
                    "GitHub API rate limit for this host (HTTP 403) — "
                    "not an outage; use an authenticated probe token or wait for reset"
                ),
            ),
        ):
            with patch.dict("os.environ", {"GITHUB_TOKEN": "", "GH_TOKEN": "", "AXON_GITHUB_TOKEN": ""}, clear=False):
                records = self.monitor_probe.probe_monitor_slice(
                    {
                        "enabled": True,
                        "workspace_id": "workspace_axon_watch",
                        "workspace_label": "Axon-X",
                        "checks": [
                            {
                                "id": "axon_x_github_api_health",
                                "type": "http_health",
                                "service": "GitHub API",
                                "url": "https://api.github.com/zen",
                            }
                        ],
                    }
                )
        self.assertEqual("warning", records[0]["status"])
        vault = records[0].get("vault_action") or {}
        self.assertEqual("/vault", vault.get("surface"))
        self.assertIn("GH_TOKEN", str(vault.get("hint") or ""))

    def test_github_bare_403_without_token_adds_vault_hint(self) -> None:
        with patch.object(
            self.monitor_probe,
            "check_http_health",
            return_value=(
                "warning",
                (
                    "GitHub API HTTP 403 from https://api.github.com/zen — "
                    "usually a missing probe token or rate limit, not a GitHub outage"
                ),
            ),
        ):
            with patch.dict("os.environ", {"GITHUB_TOKEN": "", "GH_TOKEN": "", "AXON_GITHUB_TOKEN": ""}, clear=False):
                records = self.monitor_probe.probe_monitor_slice(
                    {
                        "enabled": True,
                        "workspace_id": "workspace_axon_watch",
                        "workspace_label": "Axon-X",
                        "checks": [
                            {
                                "id": "axon_x_github_api_health",
                                "type": "http_health",
                                "service": "GitHub API",
                                "url": "https://api.github.com/zen",
                            }
                        ],
                    }
                )
        vault = records[0].get("vault_action") or {}
        self.assertEqual("/vault", vault.get("surface"))
        self.assertIn("GH_TOKEN", str(vault.get("hint") or ""))


if __name__ == "__main__":
    unittest.main()
