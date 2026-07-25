"""Validate dedicated-host readiness smoke contract for control-plane /api/readiness."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.verify.common import CheckResult, emit, load_json

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SPEC_PATH = REPO_ROOT / "config" / "dedicated-host-smoke-contract.json"
LOOPBACK_PATTERN = re.compile(r"127\.0\.0\.1|localhost", re.IGNORECASE)


def validate_dedicated_readiness(
    payload: dict[str, Any],
    *,
    spec: dict[str, Any] | None = None,
) -> CheckResult:
    spec = spec or load_json(DEFAULT_SPEC_PATH)
    required_fields = list(spec["readiness_required_fields"])
    missing = [field for field in required_fields if field not in payload]
    if missing:
        return CheckResult(
            name="dedicated_host_smoke",
            status="fail",
            message="readiness payload missing required fields",
            details=[f"missing={missing}"],
        )

    mode = str(payload.get("mode", "")).strip()
    allowed_modes = set(spec.get("allowed_modes", []))
    if allowed_modes and mode not in allowed_modes:
        return CheckResult(
            name="dedicated_host_smoke",
            status="fail",
            message=f"unexpected deployment mode: {mode!r}",
        )

    watch_base_url = str(payload.get("watch_base_url", "")).strip()
    if not watch_base_url.startswith("http"):
        return CheckResult(
            name="dedicated_host_smoke",
            status="fail",
            message="watch_base_url must be an http(s) URL",
        )

    state_dir = str(payload.get("state_dir", "")).strip()
    if not state_dir:
        return CheckResult(
            name="dedicated_host_smoke",
            status="fail",
            message="state_dir must be non-empty",
        )

    public_base_url = str(payload.get("public_base_url", "")).strip()
    if not public_base_url.startswith("http"):
        return CheckResult(
            name="dedicated_host_smoke",
            status="fail",
            message="public_base_url must be an http(s) URL",
        )

    dedicated_rules = spec.get("dedicated_rules", {})
    if mode == "dedicated":
        if dedicated_rules.get("state_dir_must_be_absolute") and not Path(state_dir).is_absolute():
            return CheckResult(
                name="dedicated_host_smoke",
                status="fail",
                message="dedicated mode requires absolute AXON_WATCH_STATE_DIR",
            )
        if (
            dedicated_rules.get("public_base_url_must_not_use_loopback")
            and LOOPBACK_PATTERN.search(public_base_url)
        ):
            return CheckResult(
                name="dedicated_host_smoke",
                status="fail",
                message="dedicated mode public_base_url must not use loopback",
            )

    return CheckResult(
        name="dedicated_host_smoke",
        status="pass",
        message=f"readiness contract satisfied for mode={mode}",
        details=[f"spec={DEFAULT_SPEC_PATH.relative_to(REPO_ROOT)}"],
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fixture",
        help="JSON readiness payload fixture path",
    )
    parser.add_argument("--spec", help="dedicated host smoke contract path")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    spec_path = Path(args.spec) if args.spec else DEFAULT_SPEC_PATH
    spec = load_json(spec_path)

    if args.fixture:
        payload = load_json(Path(args.fixture))
        if not isinstance(payload, dict):
            print("fixture must be a JSON object", file=sys.stderr)
            return 1
        return emit(validate_dedicated_readiness(payload, spec=spec))

    bootstrap_fixture = {
        "service": "control-plane",
        "status": "ready",
        "mode": "bootstrap",
        "watch_base_url": "http://127.0.0.1:8788",
        "state_dir": "./.local/state",
        "public_base_url": "http://127.0.0.1:4173",
    }
    dedicated_fixture = {
        "service": "control-plane",
        "status": "ready",
        "mode": "dedicated",
        "watch_base_url": "http://127.0.0.1:8788",
        "state_dir": "/var/lib/axon-watch/state",
        "public_base_url": "https://axon.example.com",
    }
    for label, fixture in (("bootstrap", bootstrap_fixture), ("dedicated", dedicated_fixture)):
        result = validate_dedicated_readiness(fixture, spec=spec)
        if result.status != "pass":
            print(f"{label} fixture failed: {result.message}", file=sys.stderr)
            return 1
    print("dedicated host smoke contract OK (bootstrap + dedicated fixtures)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
