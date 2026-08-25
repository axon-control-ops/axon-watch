"""P-D3 dedicated-host smoke parity tests."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTROL_PLANE_ROOT = REPO_ROOT / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.main import app  # noqa: E402


class ParityD3DedicatedHostSmokeTests(unittest.TestCase):
    def test_default_verify_wiring_includes_parity_d3_tests(self) -> None:
        from tests.verify_contract_wiring import contract_verify_wiring_surface

        verify_script = contract_verify_wiring_surface()
        self.assertIn("tests.test_parity_d3_dedicated_host_smoke", verify_script)

    def test_bootstrap_readiness_includes_public_base_url(self) -> None:
        with patch.dict(
            os.environ,
            {
                "AXON_WATCH_DEPLOYMENT_MODE": "bootstrap",
                "AXON_WATCH_STATE_DIR": "./.local/state",
                "AXON_WATCH_PUBLIC_BASE_URL": "http://127.0.0.1:4173",
            },
            clear=False,
        ):
            client = TestClient(app)
            self.addCleanup(client.close)
            response = client.get("/api/readiness")
        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual("bootstrap", payload["mode"])
        self.assertIn("public_base_url", payload)
        self.assertTrue(str(payload["public_base_url"]).startswith("http"))

    def test_simulated_dedicated_readiness_requires_absolute_state_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            state_dir = Path(tempdir).resolve()
            env = {
                "AXON_WATCH_DEPLOYMENT_MODE": "dedicated",
                "AXON_WATCH_STATE_DIR": str(state_dir),
                "AXON_WATCH_PUBLIC_BASE_URL": "https://axon.example.com",
                "AXON_WATCH_WATCH_SERVICE_BASE_URL": "http://127.0.0.1:8788",
                "AXON_WATCH_OPERATOR_TOKEN": "dedicated-readiness-token",
            }
            with patch.dict(os.environ, env, clear=False):
                client = TestClient(app)
                self.addCleanup(client.close)
                response = client.get(
                    "/api/readiness",
                    headers={"Authorization": "Bearer dedicated-readiness-token"},
                )
            self.assertEqual(200, response.status_code)
            payload = response.json()
            self.assertEqual("dedicated", payload["mode"])
            self.assertEqual(str(state_dir), payload["state_dir"])
            self.assertTrue(Path(payload["state_dir"]).is_absolute())
            self.assertNotIn("127.0.0.1", payload["public_base_url"])
            self.assertNotIn("localhost", payload["public_base_url"].lower())

    def test_dedicated_deployment_smoke_checker_passes(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/verify/check_dedicated_deployment_smoke.py"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, msg=result.stderr or result.stdout)


if __name__ == "__main__":
    unittest.main()
