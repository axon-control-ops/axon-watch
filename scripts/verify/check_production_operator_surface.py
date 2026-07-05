"""Validate production operator surface declaration."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.verify.common import CheckResult, emit, load_json

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SPEC_PATH = REPO_ROOT / "config" / "operator-production.json"
SNAPSHOT_FILE = REPO_ROOT / "config" / "parity-snapshot.json"


def validate_production_operator(*, spec: dict[str, object] | None = None) -> CheckResult:
    spec = spec or load_json(DEFAULT_SPEC_PATH)

    if spec.get("status") != "axon_x":
        return CheckResult(
            name="production_operator_surface",
            status="fail",
            message=f"unexpected production status: {spec.get('status')!r}",
        )

    primary_url = str(spec.get("primary_url", "")).strip()
    if not primary_url.startswith("http") or ":4173" not in primary_url:
        return CheckResult(
            name="production_operator_surface",
            status="fail",
            message="primary_url must target console-web on port 4173",
        )

    fallback_url = str(spec.get("fallback_url", "")).strip()
    if not fallback_url.startswith("http"):
        return CheckResult(
            name="production_operator_surface",
            status="fail",
            message="fallback_url must be an http(s) URL",
        )

    if not SNAPSHOT_FILE.is_file():
        return CheckResult(
            name="production_operator_surface",
            status="fail",
            message="parity snapshot missing",
        )

    snapshot = load_json(SNAPSHOT_FILE)
    production = snapshot.get("production_operator")
    if not isinstance(production, dict):
        return CheckResult(
            name="production_operator_surface",
            status="fail",
            message="parity snapshot missing production_operator block",
        )

    if production.get("primary_url") != primary_url:
        return CheckResult(
            name="production_operator_surface",
            status="fail",
            message="snapshot production_operator.primary_url mismatch",
        )

    doc_path = REPO_ROOT / "docs" / "PRODUCTION_OPERATOR_SURFACE.md"
    if not doc_path.is_file():
        return CheckResult(
            name="production_operator_surface",
            status="fail",
            message="missing docs/PRODUCTION_OPERATOR_SURFACE.md",
        )

    return CheckResult(
        name="production_operator_surface",
        status="pass",
        message=f"production operator declared at {primary_url}",
        details=[f"spec={DEFAULT_SPEC_PATH.relative_to(REPO_ROOT)}"],
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", help="operator production config path")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    spec_path = Path(args.spec) if args.spec else DEFAULT_SPEC_PATH
    spec = load_json(spec_path)
    return emit(validate_production_operator(spec=spec))


if __name__ == "__main__":
    raise SystemExit(main())
