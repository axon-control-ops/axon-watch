"""npm bootstrap failures must report the real error, not a deprecation warning."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.workspace_agents.workspace_runtime_bootstrap import (  # noqa: E402
    npm_failure_detail,
)


class NpmFailureDetailTests(unittest.TestCase):
    def test_deprecation_warnings_are_not_reported_as_the_failure(self) -> None:
        """Regression: dispatch was blocked with the reason

        "Workspace npm toolchain is not ready: npm warn deprecated uuid@7.0.3..."

        npm emits those warnings on healthy installs too, so it pointed the
        operator at an unrelated transitive dependency.
        """
        stderr = "\n".join(
            [
                "npm warn deprecated uuid@7.0.3: uuid@10 and below is no longer supported.",
                "npm warn deprecated glob@7.2.3: Glob versions prior to v9 are no longer supported.",
                "npm error code ERESOLVE",
                "npm error ERESOLVE unable to resolve dependency tree",
            ]
        )
        detail = npm_failure_detail(stderr, "")
        self.assertIn("ERESOLVE", detail)
        self.assertNotIn("npm warn deprecated", detail)

    def test_falls_back_to_warnings_only_when_nothing_else_exists(self) -> None:
        stderr = "npm warn deprecated uuid@7.0.3: no longer supported."
        self.assertIn("uuid@7.0.3", npm_failure_detail(stderr, ""))

    def test_uses_stdout_when_stderr_is_empty(self) -> None:
        self.assertIn("ENOSPC", npm_failure_detail("", "npm error ENOSPC no space left"))

    def test_empty_output_reports_a_usable_default(self) -> None:
        self.assertEqual("npm install failed", npm_failure_detail("", ""))
        self.assertEqual("npm install failed", npm_failure_detail("   \n  ", "\n"))

    def test_keeps_the_tail_because_npm_prints_the_real_error_last(self) -> None:
        stderr = "\n".join([f"npm error line {index}" for index in range(60)])
        detail = npm_failure_detail(stderr, "")
        self.assertIn("line 59", detail)
        self.assertLessEqual(len(detail), 400)


if __name__ == "__main__":
    unittest.main()
