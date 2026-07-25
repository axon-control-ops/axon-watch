"""Validate boot-critical runtime summary fields against planning allowlist."""

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
DEFAULT_SPEC_PATH = REPO_ROOT / "config" / "runtime-summary-boot-critical-fields.json"


def _missing_keys(payload: dict[str, Any], required: list[str], prefix: str) -> list[str]:
    return [f"{prefix}{key}" for key in required if key not in payload]


def validate_boot_critical_fields(
    payload: dict[str, Any],
    *,
    spec: dict[str, Any] | None = None,
) -> CheckResult:
    spec = spec or load_json(DEFAULT_SPEC_PATH)
    missing: list[str] = []

    missing.extend(_missing_keys(payload, spec["top_level"], ""))
    for section, keys in spec.get("nested", {}).items():
        section_payload = payload.get(section)
        if not isinstance(section_payload, dict):
            if section in spec["top_level"]:
                missing.append(f"{section} (expected object)")
            continue
        missing.extend(_missing_keys(section_payload, keys, f"{section}."))

    active_run_fields = spec.get("active_run_item", [])
    active_runs = payload.get("active_runs")
    if not isinstance(active_runs, list):
        missing.append("active_runs (expected array)")
    elif active_runs:
        first_run = active_runs[0]
        if isinstance(first_run, dict):
            missing.extend(_missing_keys(first_run, active_run_fields, "active_runs[0]."))
        else:
            missing.append("active_runs[0] (expected object)")

    if missing:
        return CheckResult(
            name="runtime_summary_boot_critical_fields",
            status="fail",
            message=f"missing {len(missing)} boot-critical field(s)",
            details=missing[:20],
        )

    return CheckResult(
        name="runtime_summary_boot_critical_fields",
        status="pass",
        message=(
            f"all boot-critical fields present ({len(spec['top_level'])} top-level sections)"
        ),
        details=[f"spec={DEFAULT_SPEC_PATH.relative_to(REPO_ROOT)}"],
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--payload",
        help="runtime summary JSON payload path (defaults to shared contract fixture)",
    )
    parser.add_argument(
        "--spec",
        help="boot-critical field allowlist path",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    payload_path = (
        Path(args.payload)
        if args.payload
        else REPO_ROOT / "packages/shared-types/fixtures/runtime-summary.example.json"
    )
    spec_path = Path(args.spec) if args.spec else DEFAULT_SPEC_PATH
    payload = load_json(payload_path)
    spec = load_json(spec_path)
    return emit(validate_boot_critical_fields(payload, spec=spec))


if __name__ == "__main__":
    raise SystemExit(main())
