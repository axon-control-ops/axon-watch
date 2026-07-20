from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TOPOLOGY_FILE = REPO_ROOT / "config" / "deployment-topology.json"
VALIDATOR = REPO_ROOT / "scripts" / "ops" / "validate_deployment_config.py"


class DeploymentReadinessTests(unittest.TestCase):
    def test_topology_startup_order_matches_spec(self) -> None:
        payload = json.loads(TOPOLOGY_FILE.read_text(encoding="utf-8"))
        self.assertEqual(
            ["storage", "axon-watch", "control-plane", "console-web", "reverse-proxy"],
            payload["startup_order"],
        )
        self.assertEqual("internal_only", payload["services"]["axon-watch"]["public_exposure"])

    def test_validate_deployment_config_script_passes(self) -> None:
        result = subprocess.run(
            [sys.executable, str(VALIDATOR)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr or result.stdout)

    def test_caddy_example_does_not_expose_watch_internals(self) -> None:
        text = (REPO_ROOT / "infra" / "caddy" / "Caddyfile.example").read_text(encoding="utf-8")
        self.assertIn("reverse_proxy", text)
        self.assertNotIn("internal/watch", text.lower())

    def test_user_systemd_units_cover_always_on_stack(self) -> None:
        user_dir = REPO_ROOT / "infra" / "systemd" / "user"
        expected = ("axon-watch.service", "control-plane.service", "console-web.service")
        for name in expected:
            path = user_dir / name
            self.assertTrue(path.is_file(), f"missing user unit: {path.relative_to(REPO_ROOT)}")
            text = path.read_text(encoding="utf-8")
            self.assertIn("EnvironmentFile=", text, f"{name} must reference EnvironmentFile=")
            self.assertIn("run-service.sh", text, f"{name} must invoke run-service.sh")

    def test_one_word_stack_bin_wrappers_resolve_to_ops_scripts(self) -> None:
        mapping = {
            "axonhealth": "scripts/ops/axonhealth.sh",
            "axonrestart": "scripts/ops/axonrestart.sh",
            "axonrevive": "scripts/ops/axonrevive.sh",
        }
        for name, rel_target in mapping.items():
            wrapper = REPO_ROOT / "bin" / name
            target = REPO_ROOT / rel_target
            self.assertTrue(wrapper.is_file(), f"missing bin wrapper: {wrapper.relative_to(REPO_ROOT)}")
            self.assertTrue(
                wrapper.stat().st_mode & 0o111,
                f"bin wrapper not executable: {wrapper.relative_to(REPO_ROOT)}",
            )
            self.assertTrue(target.is_file(), f"missing ops script: {target.relative_to(REPO_ROOT)}")
            text = wrapper.read_text(encoding="utf-8")
            self.assertIn(rel_target, text, f"{name} must exec {rel_target}")


if __name__ == "__main__":
    unittest.main()
