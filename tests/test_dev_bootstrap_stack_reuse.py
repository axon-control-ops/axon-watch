"""Regression tests for dev bootstrap reuse of an already-healthy stack."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
COMMON_SH = REPO_ROOT / "scripts" / "dev" / "lib" / "common.sh"
UP_SH = REPO_ROOT / "scripts" / "dev" / "up.sh"
RESTART_SH = REPO_ROOT / "scripts" / "dev" / "restart.sh"
SOFT_CUTOVER_SH = REPO_ROOT / "scripts" / "ops" / "soft-public-cutover.sh"
PROXY_SCRIPT = REPO_ROOT / "scripts" / "ops" / "public-origin-proxy.py"
PROXY_UNIT = REPO_ROOT / "infra" / "systemd" / "user" / "axon-public-origin-proxy.service"


class DevBootstrapStackReuseContractTests(unittest.TestCase):
    def test_restart_suspends_legacy_cutover_ports(self) -> None:
        restart_script = RESTART_SH.read_text(encoding="utf-8")

        self.assertIn("for port in 7734 7735", restart_script)
        self.assertIn("axon-public-origin-proxy.service", restart_script)
        self.assertIn(
            '"${repo_root}/scripts/dev/up.sh" --force --no-soft-cutover "$@"',
            restart_script,
        )
        self.assertIn("for attempt in 1 2 3", restart_script)
        self.assertIn("check_health_after_restart", restart_script)

    def test_up_sh_checks_health_before_pid_conflicts(self) -> None:
        up_script = UP_SH.read_text(encoding="utf-8")

        self.assertIn("try_reuse_healthy_bootstrap_stack", up_script)
        reuse_index = up_script.index("try_reuse_healthy_bootstrap_stack")
        pid_guard_index = up_script.index("assert_no_live_pid_files")
        self.assertLess(reuse_index, pid_guard_index)

    def test_up_sh_ensures_soft_public_tunnel_instead_of_legacy_7734(self) -> None:
        up_script = UP_SH.read_text(encoding="utf-8")

        self.assertIn("ensure_soft_public_tunnel", up_script)
        self.assertIn("soft-public-cutover.sh", up_script)
        self.assertIn("AXON_WATCH_ENSURE_LEGACY_7734", up_script)
        self.assertNotIn(
            'echo "Ensuring sibling axon-local server on :7734..."',
            up_script,
        )

    def test_soft_cutover_prefers_restartable_systemd_proxy(self) -> None:
        cutover = SOFT_CUTOVER_SH.read_text(encoding="utf-8")
        proxy = PROXY_SCRIPT.read_text(encoding="utf-8")
        unit = PROXY_UNIT.read_text(encoding="utf-8")

        self.assertIn("axon-public-origin-proxy.service", cutover)
        self.assertIn("systemctl --user restart", cutover)
        self.assertIn("Restart=always", unit)
        self.assertIn("After=network.target console-web.service", unit)
        self.assertIn("socket.AF_INET6", proxy)
        self.assertIn("socket.IPV6_V6ONLY, 0", proxy)

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
