import unittest

import sys
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.cli_runtime.runtime_auth import (  # noqa: E402
    env_without_api_keys,
    looks_like_auth_error,
    summarize_auth_error,
)


class RuntimeAuthTests(unittest.TestCase):
    def test_looks_like_auth_error(self) -> None:
        self.assertTrue(looks_like_auth_error("401 Unauthorized: invalid API key"))
        self.assertFalse(looks_like_auth_error("workspace root unavailable"))

    def test_env_without_api_keys_cursor(self) -> None:
        env = {"CURSOR_API_KEY": "sk-test", "PATH": "/usr/bin"}
        stripped = env_without_api_keys(env, family="cursor")
        self.assertNotIn("CURSOR_API_KEY", stripped)
        self.assertEqual("/usr/bin", stripped["PATH"])

    def test_summarize_auth_error_cursor(self) -> None:
        message = summarize_auth_error(family="cursor", detail="invalid API key provided")
        self.assertIn("/vault", message)


if __name__ == "__main__":
    unittest.main()
