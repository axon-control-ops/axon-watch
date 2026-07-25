"""Validate executive operator rhythm fields on briefing payloads."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.verify.common import CheckResult, emit, load_json

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SPEC_PATH = REPO_ROOT / "config" / "executive-operator-rhythm-contract.json"
DEFAULT_FIXTURE_PATH = (
    REPO_ROOT / "packages/shared-types/fixtures/operator-briefing.example.json"
)


def validate_executive_rhythm(
    payload: dict[str, Any],
    *,
    spec: dict[str, Any] | None = None,
) -> CheckResult:
    spec = spec or load_json(DEFAULT_SPEC_PATH)
    rhythm = payload.get("executive_rhythm")
    if not isinstance(rhythm, dict):
        return CheckResult(
            name="executive_operator_rhythm",
            status="fail",
            message="executive_rhythm block missing or not an object",
        )

    required_keys = spec["required_keys"]
    missing = [key for key in required_keys if key not in rhythm]
    empty = [key for key in required_keys if not str(rhythm.get(key, "")).strip()]
    if missing or empty:
        details = [f"missing={missing}" if missing else "", f"empty={empty}" if empty else ""]
        return CheckResult(
            name="executive_operator_rhythm",
            status="fail",
            message="executive rhythm contract incomplete",
            details=[detail for detail in details if detail],
        )

    if rhythm.get("notice") != payload.get("notice") or rhythm.get("advise") != payload.get("advise"):
        return CheckResult(
            name="executive_operator_rhythm",
            status="fail",
            message="top-level notice/advise must mirror executive_rhythm",
        )

    return CheckResult(
        name="executive_operator_rhythm",
        status="pass",
        message=f"all {len(required_keys)} rhythm fields present and mirrored",
        details=[f"spec={DEFAULT_SPEC_PATH.relative_to(REPO_ROOT)}"],
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", help="operator briefing JSON payload path")
    parser.add_argument("--spec", help="rhythm contract path")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    payload_path = Path(args.payload) if args.payload else DEFAULT_FIXTURE_PATH
    spec_path = Path(args.spec) if args.spec else DEFAULT_SPEC_PATH
    payload = load_json(payload_path)
    spec = load_json(spec_path)
    return emit(validate_executive_rhythm(payload, spec=spec))


if __name__ == "__main__":
    raise SystemExit(main())
