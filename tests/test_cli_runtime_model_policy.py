from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.cli_runtime.model_policy import (  # noqa: E402
    is_cursor_api_model,
    is_cursor_composer_model,
    resolve_cli_model_for_dispatch,
)


class CliRuntimeModelPolicyTests(unittest.TestCase):
    def test_classifier_shapes(self) -> None:
        self.assertTrue(is_cursor_composer_model("composer-2.5-fast"))
        self.assertTrue(is_cursor_api_model("gpt-5.4-high"))
        self.assertTrue(is_cursor_api_model("cursor-grok-4.5-high-fast"))
        self.assertFalse(is_cursor_api_model("auto"))
        self.assertFalse(is_cursor_api_model("composer-2"))

    def test_worker_ignores_env_api_model(self) -> None:
        with patch.dict(os.environ, {"AXON_WATCH_CURSOR_MODEL": "gpt-5.4-high"}, clear=False):
            self.assertEqual(
                resolve_cli_model_for_dispatch("cursor", "", trust_policy="worker"),
                "",
            )
            self.assertEqual(
                resolve_cli_model_for_dispatch("cursor", "auto", trust_policy="worker"),
                "",
            )

    def test_worker_allows_composer_and_explicit_api_pin(self) -> None:
        self.assertEqual(
            resolve_cli_model_for_dispatch(
                "cursor",
                "composer-2.5-fast",
                trust_policy="worker",
            ),
            "composer-2.5-fast",
        )
        self.assertEqual(
            resolve_cli_model_for_dispatch(
                "cursor",
                "gpt-5.4-high",
                trust_policy="worker",
            ),
            "gpt-5.4-high",
        )

    def test_operator_still_uses_env_fallback(self) -> None:
        with patch.dict(os.environ, {"AXON_WATCH_CURSOR_MODEL": "gpt-5.4-high"}, clear=False):
            self.assertEqual(
                resolve_cli_model_for_dispatch("cursor", "", trust_policy="operator"),
                "gpt-5.4-high",
            )


if __name__ == "__main__":
    unittest.main()
