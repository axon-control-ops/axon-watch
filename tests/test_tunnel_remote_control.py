"""G4.3 Cloudflare tunnel credential and probe tests."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

WATCH_ROOT = Path(__file__).resolve().parents[1] / "services" / "axon-watch"
sys.path.insert(0, str(WATCH_ROOT))

from app.tunnel import tunnel_control  # noqa: E402
from app.tunnel import native_process  # noqa: E402
from app.tunnel.native_process import build_cloudflared_command  # noqa: E402
from app.tunnel.tunnel_credentials import (  # noqa: E402
    resolve_cloudflare_tunnel_token_state,
)
from app.tunnel.tunnel_probe import (  # noqa: E402
    _classify_public_health_body,
    _remote_ingress_from_logs,
    build_tunnel_diagnostics,
)


class TunnelCredentialsWatchTests(unittest.TestCase):
    def test_skips_zero_byte_cloudflared_on_path(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            bad_dir = root / "bad"
            good_dir = root / "good"
            bad_dir.mkdir()
            good_dir.mkdir()
            bad_bin = bad_dir / "cloudflared"
            bad_bin.write_text("", encoding="utf-8")
            bad_bin.chmod(0o755)
            good_bin = good_dir / "cloudflared"
            good_bin.write_text("#!/bin/sh\necho cloudflared\n", encoding="utf-8")
            good_bin.chmod(0o755)
            with patch.dict(
                os.environ,
                {"PATH": f"{bad_dir}{os.pathsep}{good_dir}"},
                clear=False,
            ):
                from app.tunnel.cloudflared_binary import find_cloudflared_binary

                resolved = find_cloudflared_binary(["cloudflared"])
        self.assertEqual(str(good_bin), resolved)

    def test_prefers_environment_token(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            home = Path(tempdir)
            with patch.dict(os.environ, {"AXON_CLOUDFLARE_TUNNEL_TOKEN": "env-token"}, clear=False):
                state = resolve_cloudflare_tunnel_token_state("", home_path=home)
        self.assertEqual("env-token", state["token"])
        self.assertEqual("environment", state["source"])

    def test_uses_vault_import_when_present(self) -> None:
        with patch(
            "app.tunnel.tunnel_probe.load_tunnel_vault_secrets",
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

    def test_uses_unlocked_vault_secret_when_import_missing(self) -> None:
        with patch(
            "app.tunnel.tunnel_credentials.load_vault_import",
            return_value={},
        ), patch(
            "app.tunnel.tunnel_credentials.VaultSession.is_unlocked",
            return_value=True,
        ), patch(
            "app.tunnel.tunnel_credentials.vault_resolve_named_secret",
            side_effect=lambda name: "vault-db-token" if name == "cloudflare_tunnel_token" else "",
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
        self.assertTrue(diagnostics["tunnel"]["auth_ready"])
        self.assertIn(
            diagnostics["tunnel"]["auth_source"],
            {"settings", "vault"},
        )


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
            "app.tunnel.tunnel_probe._cloudflared_process_count",
            return_value=0,
        ), patch(
            "app.tunnel.tunnel_probe.managed_process_snapshot",
            return_value={
                "managed": False,
                "pid": None,
                "process_state_path": "",
                "log_path": "",
            },
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

    def test_parses_escaped_remote_ingress_from_cloudflared_log(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            log_path = Path(tempdir) / "cloudflared.log"
            log_path.write_text(
                'INF Updated to new configuration config="{\\"ingress\\":['
                '{\\"hostname\\":\\"axon.edudashpro.org.za\\",'
                '\\"service\\":\\"http://localhost:7734\\"},'
                '{\\"service\\":\\"http_status:404\\"}],'
                '\\"warp-routing\\":{\\"enabled\\":false}}" version=1\n',
                encoding="utf-8",
            )
            hostname, service = _remote_ingress_from_logs([str(log_path)])
        self.assertEqual("axon.edudashpro.org.za", hostname)
        self.assertEqual("http://localhost:7734", service)

    def test_classifies_control_plane_health_as_axon_x(self) -> None:
        ok, detail = _classify_public_health_body(
            '{"service":"control-plane","status":"ok"}'
        )
        self.assertTrue(ok)
        self.assertIn("axon-x", detail)

    def test_classifies_axon_local_health_as_not_axon_x(self) -> None:
        ok, detail = _classify_public_health_body(
            '{"status":"ok","port":7734,"runtime":{"repo_root":"/home/edp/axon-nvme/repos/axon-local"}}'
        )
        self.assertFalse(ok)
        self.assertIn("axon-local", detail)

    def test_soft_origin_cutover_ok_when_public_is_axon_x(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            log_path = Path(tempdir) / "cloudflared.log"
            log_path.write_text(
                'INF config="{\\"ingress\\":[{\\"hostname\\":\\"axon.example\\",'
                '\\"service\\":\\"http://localhost:7734\\"},'
                '{\\"service\\":\\"http_status:404\\"}]}"\n',
                encoding="utf-8",
            )
            with patch(
                "app.tunnel.tunnel_probe.find_cloudflared_binary",
                return_value="/usr/bin/cloudflared",
            ), patch(
                "app.tunnel.tunnel_probe.cloudflared_version",
                return_value="cloudflared version test",
            ), patch(
                "app.tunnel.tunnel_probe._tunnel_process_running",
                return_value=True,
            ), patch(
                "app.tunnel.tunnel_probe._cloudflared_process_count",
                return_value=1,
            ), patch(
                "app.tunnel.tunnel_probe.managed_process_snapshot",
                return_value={
                    "managed": True,
                    "pid": 123,
                    "process_state_path": "",
                    "log_path": str(log_path),
                },
            ), patch(
                "app.tunnel.tunnel_probe.resolve_cloudflare_tunnel_token_state",
                return_value={"token": "token", "source": "environment"},
            ), patch(
                "app.tunnel.tunnel_probe.named_tunnel_ready",
                return_value=True,
            ), patch(
                "app.tunnel.tunnel_probe._probe_public_axon_x",
                return_value=(True, 12, "axon-x control-plane"),
            ):
                diagnostics = build_tunnel_diagnostics(
                    {
                        "enabled": True,
                        "connector_id": "cloudflare_tunnel",
                        "display_name": "Cloudflare tunnel",
                        "tunnel_mode": "named",
                        "public_base_url": "https://axon.example",
                        "local_origin_url": "http://127.0.0.1:4173",
                        "binary_candidates": ["cloudflared"],
                        "tunnel_log_paths": [str(log_path)],
                    }
                )
        self.assertEqual("ok", diagnostics["status"])
        self.assertTrue(diagnostics["tunnel"]["soft_origin_cutover"])
        self.assertIn("soft cutover", diagnostics["detail"])


class NativeTunnelControlTests(unittest.TestCase):
    def test_named_command_keeps_token_out_of_process_arguments(self) -> None:
        command, env = build_cloudflared_command(
            {"tunnel_mode": "named"},
            "/usr/bin/cloudflared",
            token="secret-token",
        )

        self.assertEqual(
            ["/usr/bin/cloudflared", "--no-autoupdate", "tunnel", "run"],
            command,
        )
        self.assertNotIn("secret-token", command)
        self.assertEqual("secret-token", env["TUNNEL_TOKEN"])

    def test_trycloudflare_command_uses_configured_local_origin(self) -> None:
        command, _ = build_cloudflared_command(
            {
                "tunnel_mode": "trycloudflare",
                "local_origin_url": "http://127.0.0.1:4173",
            },
            "/usr/bin/cloudflared",
        )

        self.assertIn("http://127.0.0.1:4173", command)

    def test_trycloudflare_defaults_to_axon_x_operator_origin(self) -> None:
        command, _ = build_cloudflared_command(
            {"tunnel_mode": "trycloudflare"},
            "/usr/bin/cloudflared",
        )

        self.assertIn("http://127.0.0.1:4173", command)
        self.assertNotIn("http://127.0.0.1:7734", command)

    def test_start_uses_native_process_manager(self) -> None:
        stopped = {
            "running": False,
            "mode": "named",
            "binary_path": "/usr/bin/cloudflared",
            "named_tunnel_ready": True,
        }
        running = {**stopped, "running": True, "managed": True, "pid": 4321}
        with patch.object(
            tunnel_control,
            "tunnel_status",
            side_effect=[stopped, running],
        ), patch.object(
            tunnel_control,
            "_resolved_tunnel_token",
            return_value="token",
        ), patch.object(
            tunnel_control,
            "start_managed_process",
            return_value=4321,
        ) as start_process:
            result = tunnel_control.tunnel_start({"tunnel_mode": "named"})

        start_process.assert_called_once_with(
            {"tunnel_mode": "named"},
            binary_path="/usr/bin/cloudflared",
            token="token",
        )
        self.assertEqual("Tunnel started natively (PID 4321)", result["msg"])

    def test_stop_refuses_to_kill_unmanaged_tunnel(self) -> None:
        with patch.object(
            tunnel_control,
            "tunnel_status",
            return_value={"running": True, "managed": False},
        ):
            with self.assertRaisesRegex(
                tunnel_control.TunnelControlError,
                "not managed by Axon-X",
            ):
                tunnel_control.tunnel_stop({"tunnel_mode": "named"})

    def test_start_reports_unmanaged_tunnel_without_taking_ownership(self) -> None:
        with patch.object(
            tunnel_control,
            "tunnel_status",
            return_value={"running": True, "managed": False},
        ), patch.object(tunnel_control, "start_managed_process") as start_process:
            result = tunnel_control.tunnel_start({"tunnel_mode": "named"})

        start_process.assert_not_called()
        self.assertIn("not managed by Axon-X", result["msg"])

    def test_start_terminates_process_when_ownership_state_cannot_persist(self) -> None:
        process = Mock(pid=4321)
        process.poll.return_value = None
        process.wait.return_value = 0
        with tempfile.TemporaryDirectory() as tempdir:
            config = {
                "tunnel_mode": "trycloudflare",
                "native_log_path": str(Path(tempdir) / "cloudflared.log"),
            }
            with patch.object(
                native_process,
                "managed_process_snapshot",
                return_value={"managed": False, "pid": None},
            ), patch.object(
                native_process.subprocess,
                "Popen",
                return_value=process,
            ), patch.object(
                native_process,
                "_write_process_state",
                side_effect=PermissionError("read only"),
            ), patch.object(
                native_process.os,
                "killpg",
            ) as kill_group, patch.object(
                native_process.time,
                "sleep",
            ):
                with self.assertRaises(PermissionError):
                    native_process.start_managed_process(
                        config,
                        binary_path="/usr/bin/cloudflared",
                    )

        kill_group.assert_called_once_with(4321, native_process.signal.SIGTERM)
        process.wait.assert_called_once_with(timeout=5)


if __name__ == "__main__":
    unittest.main()
