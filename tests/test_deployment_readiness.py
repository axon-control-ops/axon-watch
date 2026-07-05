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


if __name__ == "__main__":
    unittest.main()
