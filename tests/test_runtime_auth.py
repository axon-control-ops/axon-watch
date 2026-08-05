import unittest

import sys
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.cli_runtime.runtime_auth import (  # noqa: E402
    codex_dispatch_env,
    codex_subscription_ready,
    cursor_dispatch_env,
    cursor_subscription_ready,
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
        message = summarize_auth_error(
            family="cursor",
            detail="invalid API key provided",
            had_api_key=True,
        )
        self.assertIn("/vault", message)
        generic = summarize_auth_error(
            family="cursor",
            detail="authentication required",
            had_api_key=False,
        )
        self.assertIn("cursor agent login", generic)
        self.assertNotIn("CURSOR_API_KEY", generic)

    def test_cursor_subscription_ready(self) -> None:
        self.assertTrue(
            cursor_subscription_ready({"auth_method": "oauth", "message": "Authenticated."})
        )
        self.assertTrue(
            cursor_subscription_ready(
                {
                    "auth_method": "vault_api_key",
                    "message": "Cursor subscription is ready.",
                }
            )
        )
        self.assertFalse(cursor_subscription_ready({"auth_method": "vault_api_key"}))

    def test_cursor_dispatch_env_strips_key_for_subscription(self) -> None:
        env = {"CURSOR_API_KEY": "sk-stale", "PATH": "/usr/bin"}
        stripped = cursor_dispatch_env(
            env,
            auth={"auth_method": "oauth", "message": "Authenticated with Cursor subscription."},
        )
        self.assertNotIn("CURSOR_API_KEY", stripped)
        self.assertEqual("/usr/bin", stripped["PATH"])

    def test_cursor_dispatch_env_keeps_key_for_headless(self) -> None:
        env = {"CURSOR_API_KEY": "sk-valid", "PATH": "/usr/bin"}
        kept = cursor_dispatch_env(
            env,
            auth={"auth_method": "vault_api_key", "message": "Authenticated via CURSOR_API_KEY"},
        )
        self.assertEqual("sk-valid", kept["CURSOR_API_KEY"])

    def test_codex_subscription_ready_and_dispatch_env(self) -> None:
        self.assertTrue(codex_subscription_ready({"auth_method": "chatgpt"}))
        env = {"CODEX_API_KEY": "stale", "OPENAI_API_KEY": "also-stale", "PATH": "/usr/bin"}
        stripped = codex_dispatch_env(env, auth={"auth_method": "chatgpt"})
        self.assertNotIn("CODEX_API_KEY", stripped)
        self.assertNotIn("OPENAI_API_KEY", stripped)
        self.assertEqual("/usr/bin", stripped["PATH"])


if __name__ == "__main__":
    unittest.main()
