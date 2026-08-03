"""Gate 6 test check must use a timeout-safe suite (not the full contract runner)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.project_contract.loader import (  # noqa: E402
    load_project_contract,
    resolve_default_contract,
)
from app.workspace_agents.verifier_runner import check_timeout_seconds  # noqa: E402


class Gate6TimeoutSafeSuiteTests(unittest.TestCase):
    def test_repo_contract_points_test_check_at_gate6_runner(self) -> None:
        contract = load_project_contract(resolve_default_contract(REPO_ROOT))
        test_cmds = [
            str(item) for item in (contract.get("commands") or {}).get("test") or []
        ]
        self.assertTrue(
            any("run_gate6_unit_tests.sh" in item for item in test_cmds),
            f"expected Gate 6 test runner in commands.test, got {test_cmds!r}",
        )
        self.assertFalse(
            any("run_contract_unit_tests.sh" in item for item in test_cmds),
            "full contract suite belongs in Fast Gate/CI, not the Gate 6 test check",
        )

    def test_gate6_runner_script_covers_verifier_contract(self) -> None:
        runner = REPO_ROOT / "scripts/verify/run_gate6_unit_tests.sh"
        self.assertTrue(runner.is_file(), f"missing {runner}")
        text = runner.read_text(encoding="utf-8")
        self.assertIn("tests.test_gate6_verifier_contract", text)
        self.assertIn("tests.test_gate6_project_contract", text)
        self.assertIn("tests.test_gate6_timeout_safe_suite", text)

    def test_default_check_timeout_covers_gate6_suite(self) -> None:
        self.assertGreaterEqual(check_timeout_seconds(), 180.0)

    def test_frontend_checks_use_path_aware_gate6_wrapper(self) -> None:
        contract = load_project_contract(resolve_default_contract(REPO_ROOT))
        commands = contract.get("commands") or {}
        for name in ("typecheck", "build"):
            cmds = [str(item) for item in commands.get(name) or []]
            self.assertTrue(
                any("run_gate6_frontend_check.sh" in item for item in cmds),
                f"expected Gate 6 frontend wrapper for {name}, got {cmds!r}",
            )
        wrapper = REPO_ROOT / "scripts/verify/run_gate6_frontend_check.sh"
        self.assertTrue(wrapper.is_file(), f"missing {wrapper}")


if __name__ == "__main__":
    unittest.main()
