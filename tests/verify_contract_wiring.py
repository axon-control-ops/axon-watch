"""Shared helpers for verify:contracts wiring tests."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_TEST_RUNNER = REPO_ROOT / "scripts" / "verify" / "run_contract_unit_tests.sh"


def contract_verify_wiring_surface() -> str:
    """Return package.json script plus runner contents for wiring assertions."""
    package = json.loads((REPO_ROOT / "package.json").read_text(encoding="utf-8"))
    script_line = package["scripts"]["verify:contracts"]
    runner_body = (
        CONTRACT_TEST_RUNNER.read_text(encoding="utf-8")
        if CONTRACT_TEST_RUNNER.is_file()
        else ""
    )
    return f"{script_line}\n{runner_body}"
