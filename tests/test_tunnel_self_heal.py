"""Milestone 0 — pinned cloudflared install and tunnel supervisor reconciliation."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.support.watch_app_loader import prepare_watch_imports, restore_app_modules

PAYLOAD = b"#!/bin/sh\necho cloudflared version 9.9.9\n"
DIGEST = hashlib.sha256(PAYLOAD).hexdigest()


def _pin(root: Path, *, digest: str = DIGEST) -> dict[str, object]:
    return {
        "schema_version": 1,
        "version": "9.9.9",
        "download_base_url": "https://example.invalid/releases/download",
        "install_root": str(root),
        "artifacts": {
            "linux/x86_64": {"asset": "cloudflared-linux-amd64", "sha256": digest},
        },
    }


class WatchModuleTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._saved_modules = prepare_watch_imports()

    def tearDown(self) -> None:
        restore_app_modules(self._saved_modules)


class CloudflaredInstallerTests(WatchModuleTestCase):
    def _installer(self):
        from app.tunnel import cloudflared_installer  # noqa: WPS433

        return cloudflared_installer

    def test_install_writes_verified_binary_and_current_symlink(self) -> None:
        installer = self._installer()
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            pin = _pin(root)
            with patch.object(installer, "platform_key", return_value="linux/x86_64"), patch.object(
                installer, "_download", side_effect=lambda url, dest, **_: dest.write_bytes(PAYLOAD)
            ):
                result = installer.install_cloudflared(pin=pin)
            self.assertTrue(result["ok"])
            self.assertTrue(result["changed"])
            binary = root / "current" / "cloudflared"
            self.assertTrue(binary.is_file())
            self.assertEqual(PAYLOAD, binary.read_bytes())
            self.assertTrue(os.access(binary, os.X_OK))
            self.assertEqual("9.9.9", (root / "current").readlink().name)

    def test_install_rejects_checksum_mismatch_and_installs_nothing(self) -> None:
        installer = self._installer()
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            pin = _pin(root, digest="0" * 64)
            with patch.object(installer, "platform_key", return_value="linux/x86_64"), patch.object(
                installer, "_download", side_effect=lambda url, dest, **_: dest.write_bytes(PAYLOAD)
            ):
                with self.assertRaises(installer.CloudflaredInstallError) as caught:
                    installer.install_cloudflared(pin=pin)
            self.assertIn("checksum mismatch", str(caught.exception))
            self.assertFalse((root / "9.9.9" / "cloudflared").exists())
            self.assertFalse((root / "current").exists())

    def test_install_refuses_non_https_download_base(self) -> None:
        installer = self._installer()
        with tempfile.TemporaryDirectory() as tempdir:
            pin = _pin(Path(tempdir))
            pin["download_base_url"] = "http://example.invalid/dl"
            with patch.object(installer, "platform_key", return_value="linux/x86_64"):
                with self.assertRaises(installer.CloudflaredInstallError):
                    installer.install_cloudflared(pin=pin)

    def test_unsupported_platform_is_reported_not_installed(self) -> None:
        installer = self._installer()
        with tempfile.TemporaryDirectory() as tempdir:
            pin = _pin(Path(tempdir))
            with patch.object(installer, "platform_key", return_value="plan9/vax"):
                diagnostics = installer.installer_diagnostics(pin=pin)
        self.assertFalse(diagnostics["platform_supported"])
        self.assertFalse(diagnostics["installed"])

    def test_diagnostics_flag_upgrade_when_installed_version_drifts(self) -> None:
        installer = self._installer()
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            pin = _pin(root)
            target = root / "current"
            target.mkdir(parents=True)
            binary = target / "cloudflared"
            binary.write_bytes(PAYLOAD)
            binary.chmod(0o755)
            with patch.object(installer, "platform_key", return_value="linux/x86_64"), patch.object(
                installer, "cloudflared_version", return_value="cloudflared version 1.0.0 (built x)"
            ):
                diagnostics = installer.installer_diagnostics(pin=pin)
        self.assertTrue(diagnostics["installed"])
        self.assertEqual("1.0.0", diagnostics["installed_version"])
        self.assertTrue(diagnostics["upgrade_available"])


class TunnelSupervisorTests(WatchModuleTestCase):
    def _supervisor_module(self):
        from app.tunnel import tunnel_supervisor  # noqa: WPS433

        return tunnel_supervisor

    def _make(self, module):
        return module.TunnelSupervisor(
            interval_seconds=0.01,
            base_backoff_seconds=1.0,
            max_backoff_seconds=8.0,
        )

    def test_restarts_process_when_managed_cloudflared_died(self) -> None:
        module = self._supervisor_module()
        supervisor = self._make(module)
        started: list[bool] = []

        def fake_start(config):
            started.append(True)
            return {"running": True}

        with patch.object(module, "load_tunnel_slice", return_value={"stable_domain": "x"}), patch.object(
            module, "managed_process_snapshot", return_value={"managed": False}
        ), patch.object(
            module, "probe_local_origin", return_value={"healthy": True, "detail": "reachable"}
        ), patch.object(module, "tunnel_start", side_effect=fake_start):
            health = supervisor.reconcile_once()

        self.assertEqual([True], started)
        self.assertTrue(health["process_alive"])
        self.assertEqual(0, health["retry_count"])
        self.assertEqual("", health["failure_reason"])
        self.assertTrue(health["last_connected_at"])

    def test_does_not_start_tunnel_over_a_dead_local_origin(self) -> None:
        module = self._supervisor_module()
        supervisor = self._make(module)

        with patch.object(module, "load_tunnel_slice", return_value={}), patch.object(
            module, "managed_process_snapshot", return_value={"managed": False}
        ), patch.object(
            module,
            "probe_local_origin",
            return_value={"healthy": False, "detail": "connection refused"},
        ), patch.object(module, "tunnel_start") as start:
            health = supervisor.reconcile_once()

        start.assert_not_called()
        self.assertFalse(health["local_origin_healthy"])
        self.assertIn("connection refused", health["failure_reason"])
        self.assertEqual(1, health["retry_count"])

    def test_backoff_grows_and_is_capped(self) -> None:
        module = self._supervisor_module()
        supervisor = self._make(module)
        delays = []
        for attempt in range(1, 7):
            supervisor._retry_count = attempt
            delays.append(supervisor._backoff_seconds())
        # base 1s doubling, jittered +/-20%, capped at 8s.
        self.assertLess(delays[0], delays[3])
        self.assertLessEqual(max(delays), 8.0 * 1.2)

    def test_failed_start_backs_off_instead_of_hammering(self) -> None:
        module = self._supervisor_module()
        supervisor = self._make(module)

        with patch.object(module, "load_tunnel_slice", return_value={}), patch.object(
            module, "managed_process_snapshot", return_value={"managed": False}
        ), patch.object(
            module, "probe_local_origin", return_value={"healthy": True, "detail": "ok"}
        ), patch.object(
            module,
            "tunnel_start",
            side_effect=module.TunnelControlError("cloudflared binary not found"),
        ) as start, patch.object(
            module, "installer_diagnostics", return_value={"installed": False}
        ):
            first = supervisor.reconcile_once()
            second = supervisor.reconcile_once()

        # Second pass is inside the backoff window, so it must not retry the start.
        self.assertEqual(1, start.call_count)
        self.assertEqual(1, first["retry_count"])
        self.assertEqual(1, second["retry_count"])
        self.assertIn("install-cloudflared.sh", first["failure_reason"])

    def test_operator_stop_pauses_reconciliation_until_resume(self) -> None:
        module = self._supervisor_module()
        supervisor = self._make(module)
        supervisor.pause("stopped by operator")

        with patch.object(module, "load_tunnel_slice", return_value={}), patch.object(
            module, "managed_process_snapshot", return_value={"managed": False}
        ), patch.object(module, "tunnel_start") as start:
            health = supervisor.reconcile_once()
        start.assert_not_called()
        self.assertEqual("stopped by operator", health["paused_reason"])

        supervisor.resume()
        with patch.object(module, "load_tunnel_slice", return_value={}), patch.object(
            module, "managed_process_snapshot", return_value={"managed": False}
        ), patch.object(
            module, "probe_local_origin", return_value={"healthy": True, "detail": "ok"}
        ), patch.object(module, "tunnel_start", return_value={"running": True}) as start:
            supervisor.reconcile_once()
        start.assert_called_once()

    def test_reconcile_survives_unexpected_errors(self) -> None:
        module = self._supervisor_module()
        supervisor = self._make(module)

        with patch.object(module, "load_tunnel_slice", return_value={}), patch.object(
            module, "managed_process_snapshot", return_value={"managed": False}
        ), patch.object(
            module, "probe_local_origin", return_value={"healthy": True, "detail": "ok"}
        ), patch.object(module, "tunnel_start", side_effect=RuntimeError("boom")), patch.object(
            module, "installer_diagnostics", return_value={"installed": True}
        ):
            health = supervisor.reconcile_once()

        self.assertIn("boom", health["failure_reason"])
        self.assertEqual(1, health["retry_count"])

    def test_edge_state_reports_hostname_mismatch(self) -> None:
        module = self._supervisor_module()
        supervisor = module.TunnelSupervisor(interval_seconds=0.01, edge_check_every=1)
        config = {"stable_domain": "axon.edudashpro.org.za"}
        diagnostics = {
            "tunnel": {"public_health_ok": True, "remote_ingress_hostname": "stale.example.com"}
        }

        with patch.object(module, "load_tunnel_slice", return_value=config), patch.object(
            module, "managed_process_snapshot", return_value={"managed": True}
        ), patch.object(module, "build_tunnel_diagnostics", return_value=diagnostics):
            health = supervisor.reconcile_once()

        self.assertTrue(health["edge_reachable"])
        self.assertEqual("stale.example.com", health["hostname"])
        self.assertFalse(health["hostname_correct"])

    def test_slice_disabled_is_reported_without_starting(self) -> None:
        module = self._supervisor_module()
        supervisor = self._make(module)
        with patch.object(module, "load_tunnel_slice", return_value=None), patch.object(
            module, "tunnel_start"
        ) as start:
            health = supervisor.reconcile_once()
        start.assert_not_called()
        self.assertIn("slice disabled", health["failure_reason"])


class ShippedPinTests(unittest.TestCase):
    def test_repo_pin_is_https_and_fully_checksummed(self) -> None:
        root = Path(__file__).resolve().parents[1]
        pin = json.loads((root / "config" / "cloudflared-pin.json").read_text(encoding="utf-8"))
        self.assertTrue(str(pin["download_base_url"]).startswith("https://"))
        self.assertTrue(str(pin["version"]).strip())
        self.assertTrue(pin["artifacts"])
        for key, entry in pin["artifacts"].items():
            self.assertEqual(64, len(entry["sha256"]), key)
            self.assertTrue(entry["asset"], key)


if __name__ == "__main__":
    unittest.main()
