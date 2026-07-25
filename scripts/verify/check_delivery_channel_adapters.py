"""Validate delivery channel adapter modules are present and registered."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.verify.common import CheckResult, emit, load_json

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SPEC_PATH = REPO_ROOT / "config" / "delivery-channels-contract.json"
ADAPTER_ROOT = REPO_ROOT / "services" / "axon-watch" / "app" / "delivery"


def validate_delivery_adapters(*, spec: dict[str, object] | None = None) -> CheckResult:
    spec = spec or load_json(DEFAULT_SPEC_PATH)
    required = list(spec["required_adapters"])
    registry_path = ADAPTER_ROOT / "adapters" / "registry.py"
    if not registry_path.is_file():
        return CheckResult(
            name="delivery_channel_adapters",
            status="fail",
            message="delivery adapter registry missing",
        )

    registry_text = registry_path.read_text(encoding="utf-8")
    missing = [name for name in required if f'"{name}"' not in registry_text]
    if missing:
        return CheckResult(
            name="delivery_channel_adapters",
            status="fail",
            message="delivery adapter registry incomplete",
            details=[f"missing={missing}"],
        )

    for module_name in ("retry.py", "config.py", "service.py"):
        if not (ADAPTER_ROOT / module_name).is_file():
            return CheckResult(
                name="delivery_channel_adapters",
                status="fail",
                message=f"missing delivery module: {module_name}",
            )

    return CheckResult(
        name="delivery_channel_adapters",
        status="pass",
        message=f"all {len(required)} delivery adapters registered",
        details=[f"spec={DEFAULT_SPEC_PATH.relative_to(REPO_ROOT)}"],
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", help="delivery channels contract path")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    spec_path = Path(args.spec) if args.spec else DEFAULT_SPEC_PATH
    spec = load_json(spec_path)
    return emit(validate_delivery_adapters(spec=spec))


if __name__ == "__main__":
    raise SystemExit(main())
