from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.cli_runtime import runtime_auth_actions  # noqa: E402


class RuntimeAuthActionsTests(unittest.TestCase):
    def setUp(self) -> None:
        runtime_auth_actions.invalidate_runtime_snapshot_cache()

    @patch("app.cli_runtime.runtime_auth_actions.find_cursor_cli", return_value="")
    @patch("app.cli_runtime.runtime_auth_actions._runtime_target", return_value=None)
    def test_logout_cursor_requires_install(self, _target, _find) -> None:
        result = runtime_auth_actions.logout_cursor_runtime()
        self.assertEqual("manual_required", result["status"])
        self.assertIn("not installed", result["message"].lower())

    @patch("app.cli_runtime.runtime_auth_actions.cursor_runtime_snapshot", return_value={})
    @patch("app.cli_runtime.runtime_auth_actions.runtime_status_snapshot", return_value={})
    @patch("app.cli_runtime.runtime_auth_actions.invalidate_runtime_snapshot_cache")
    @patch("app.cli_runtime.runtime_auth_actions._runtime_target")
    @patch("app.cli_runtime.runtime_auth_actions.find_cursor_cli", return_value="/usr/bin/cursor")
    @patch("app.cli_runtime.runtime_auth_actions.subprocess.run")
    def test_logout_cursor_clears_auth(
        self,
        mock_run,
        _find,
        mock_target,
        _invalidate,
        _snapshot,
        _cursor_snapshot,
    ) -> None:
        mock_target.side_effect = [
            {
                "family": "cursor",
                "auth": {"logged_in": True, "auth_method": "oauth"},
            },
            {"family": "cursor", "auth": {"logged_in": False}},
        ]
        mock_run.return_value = type(
            "Proc",
            (),
            {"returncode": 0, "stdout": "Signed out", "stderr": ""},
        )()
        result = runtime_auth_actions.logout_cursor_runtime()
        self.assertEqual("completed", result["status"])
        mock_run.assert_any_call(
            ["/usr/bin/cursor", "agent", "logout"],
            capture_output=True,
            text=True,
            timeout=12,
            env=mock_run.call_args.kwargs["env"],
        )


if __name__ == "__main__":
    unittest.main()
