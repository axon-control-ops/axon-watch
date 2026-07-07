"""G4.3 Cloudflare tunnel credential and probe tests."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

WATCH_ROOT = Path(__file__).resolve().parents[1] / "services" / "axon-watch"
sys.path.insert(0, str(WATCH_ROOT))

from app.tunnel.tunnel_credentials import (  # noqa: E402
    resolve_cloudflare_tunnel_token_state,
)
from app.tunnel.tunnel_probe import build_tunnel_diagnostics  # noqa: E402


class TunnelCredentialsWatchTests(unittest.TestCase):
    def test_prefers_environment_token(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            home = Path(tempdir)
            with patch.dict(os.environ, {"AXON_CLOUDFLARE_TUNNEL_TOKEN": "env-token"}, clear=False):
                state = resolve_cloudflare_tunnel_token_state("", home_path=home)
        self.assertEqual("env-token", state["token"])
        self.assertEqual("environment", state["source"])

    def test_uses_vault_import_when_present(self) -> None:
        with patch(
            "app.tunnel.tunnel_probe.load_vault_import",
            return_value={"AXON_CLOUDFLARE_TUNNEL_TOKEN": "vault-token"},
        ), patch(
            "app.tunnel.tunnel_probe.find_cloudflared_binary",
            return_value="/usr/bin/cloudflared",
        ), patch(
            "app.tunnel.tunnel_probe._tunnel_process_running",
            return_value=False,
        ):
            diagnostics = build_tunnel_diagnostics(
                {
                    "enabled": True,
                    "connector_id": "cloudflare_tunnel",
                    "display_name": "Cloudflare tunnel",
                    "tunnel_mode": "named",
                    "public_base_url": "https://example.test",
                    "binary_candidates": ["cloudflared"],
                }
            )
        self.assertEqual("vault", diagnostics["tunnel"]["auth_source"])
        self.assertTrue(diagnostics["tunnel"]["auth_ready"])


class TunnelProbeWatchTests(unittest.TestCase):
    def test_marks_missing_binary_unavailable(self) -> None:
        diagnostics = build_tunnel_diagnostics(
            {
                "enabled": True,
                "connector_id": "cloudflare_tunnel",
                "display_name": "Cloudflare tunnel",
                "tunnel_mode": "named",
                "public_base_url": "https://example.test",
                "binary_candidates": ["/nonexistent/cloudflared"],
            }
        )
        self.assertEqual("unavailable", diagnostics["status"])
        self.assertIn("binary", diagnostics["detail"].lower())

    def test_marks_stopped_tunnel_degraded_when_auth_ready(self) -> None:
        with patch(
            "app.tunnel.tunnel_probe.find_cloudflared_binary",
            return_value="/usr/bin/cloudflared",
        ), patch(
            "app.tunnel.tunnel_probe.cloudflared_version",
            return_value="cloudflared version test",
        ), patch(
            "app.tunnel.tunnel_probe._tunnel_process_running",
            return_value=False,
        ), patch(
            "app.tunnel.tunnel_probe.resolve_cloudflare_tunnel_token_state",
            return_value={"token": "token", "source": "environment"},
        ), patch(
            "app.tunnel.tunnel_probe.named_tunnel_ready",
            return_value=True,
        ):
            diagnostics = build_tunnel_diagnostics(
                {
                    "enabled": True,
                    "connector_id": "cloudflare_tunnel",
                    "display_name": "Cloudflare tunnel",
                    "tunnel_mode": "named",
                    "public_base_url": "https://example.test",
                    "binary_candidates": ["cloudflared"],
                }
            )
        self.assertEqual("degraded", diagnostics["status"])
        self.assertIn("stopped", diagnostics["detail"].lower())


if __name__ == "__main__":
    unittest.main()
