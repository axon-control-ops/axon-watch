"""Regression tests for dev bootstrap reuse of an already-healthy stack."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
COMMON_SH = REPO_ROOT / "scripts" / "dev" / "lib" / "common.sh"
UP_SH = REPO_ROOT / "scripts" / "dev" / "up.sh"


class DevBootstrapStackReuseContractTests(unittest.TestCase):
    def test_up_sh_checks_health_before_pid_conflicts(self) -> None:
        up_script = UP_SH.read_text(encoding="utf-8")

        self.assertIn("try_reuse_healthy_bootstrap_stack", up_script)
        reuse_index = up_script.index("try_reuse_healthy_bootstrap_stack")
        pid_guard_index = up_script.index("assert_no_live_pid_files")
        self.assertLess(reuse_index, pid_guard_index)

    def test_up_sh_ensures_managed_tunnel_without_legacy_axon_local(self) -> None:
        up_script = UP_SH.read_text(encoding="utf-8")
        common_script = COMMON_SH.read_text(encoding="utf-8")

        self.assertIn("ensure_managed_tunnel", up_script)
        self.assertIn("/api/tunnel/start", up_script)
        self.assertIn("--no-public-tunnel", up_script)
        self.assertNotIn("soft-public-cutover.sh", up_script)
        self.assertNotIn("AXON_WATCH_ENSURE_LEGACY_7734", up_script)
        self.assertNotIn("AXON_LOCAL_ROOT", up_script)
        self.assertNotIn("7734", up_script)
        self.assertIn("DEV_SKIP_PUBLIC_TUNNEL", common_script)
        self.assertIn("AXON_WATCH_SKIP_PUBLIC_TUNNEL", common_script)

    def test_legacy_public_origin_proxy_files_are_retired(self) -> None:
        retired_paths = [
            REPO_ROOT / "scripts" / "ops" / "soft-public-cutover.sh",
            REPO_ROOT / "scripts" / "ops" / "public-origin-proxy.py",
            REPO_ROOT / "infra" / "systemd" / "user" / "axon-public-origin-proxy.service",
        ]

        for path in retired_paths:
            self.assertFalse(path.exists(), f"{path.relative_to(REPO_ROOT)} should stay retired")

    def test_common_sh_skips_systemd_listeners_during_orphan_cleanup(self) -> None:
        common_script = COMMON_SH.read_text(encoding="utf-8")

        self.assertIn("bootstrap_stack_healthy", common_script)
        self.assertIn("try_reuse_healthy_bootstrap_stack", common_script)
        self.assertIn("listener_managed_externally", common_script)
        self.assertIn('listener_managed_externally "${pid}"', common_script)

    def test_bootstrap_stack_healthy_requires_all_services(self) -> None:
        repo = str(REPO_ROOT)
        healthy_result = subprocess.run(
            [
                "bash",
                "-c",
                f"""
                set -euo pipefail
                source "{repo}/scripts/dev/lib/common.sh"
                service_health_ready() {{ return 0; }}
                bootstrap_stack_healthy
                """,
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(0, healthy_result.returncode, msg=healthy_result.stderr)

        degraded_result = subprocess.run(
            [
                "bash",
                "-c",
                f"""
                set -euo pipefail
                source "{repo}/scripts/dev/lib/common.sh"
                service_health_ready() {{
                  [[ "$1" == "console-web" ]]
                }}
                bootstrap_stack_healthy
                """,
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(0, degraded_result.returncode)

    def test_up_sh_reuses_live_stack_when_health_checks_pass(self) -> None:
        health = subprocess.run(
            [str(REPO_ROOT / "scripts" / "dev" / "check-health.sh")],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if health.returncode != 0:
            self.skipTest("live bootstrap stack is not up")

        reuse = subprocess.run(
            [str(UP_SH)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(0, reuse.returncode, msg=reuse.stderr or reuse.stdout)
        self.assertIn("already healthy", reuse.stdout.lower())


if __name__ == "__main__":
    unittest.main()
