from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.verify.common import CheckResult, compact_json_size_bytes, emit_many, load_config


def _evaluate_payload(
    payload_name: str,
    payload_path: Path | None,
    threshold_bytes: int,
    strict_pending: bool,
) -> CheckResult:
    if payload_path is None:
        status = "fail" if strict_pending else "pending"
        return CheckResult(
            name=f"{payload_name}_dto_size",
            status=status,
            message="no payload fixture or captured body supplied yet",
            details=[f"threshold={threshold_bytes} bytes"],
        )

    actual_bytes = compact_json_size_bytes(payload_path)
    if actual_bytes <= threshold_bytes:
        return CheckResult(
            name=f"{payload_name}_dto_size",
            status="pass",
            message=f"{actual_bytes} bytes <= {threshold_bytes} bytes",
            details=[f"source={payload_path}"],
        )

    return CheckResult(
        name=f"{payload_name}_dto_size",
        status="fail",
        message=f"{actual_bytes} bytes > {threshold_bytes} bytes",
        details=[f"source={payload_path}"],
    )


def run_check(
    runtime_payload: Path | None = None,
    watch_payload: Path | None = None,
    strict_pending: bool = False,
) -> list[CheckResult]:
    config = load_config()["dto_sizes"]
    return [
        _evaluate_payload(
            "runtime_summary",
            runtime_payload,
            int(config["runtime_summary"]["threshold_bytes"]),
            strict_pending,
        ),
        _evaluate_payload(
            "watch_summary",
            watch_payload,
            int(config["watch_summary"]["threshold_bytes"]),
            strict_pending,
        ),
    ]


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check Axon-Watch DTO payload size budgets.")
    parser.add_argument("--runtime-payload", help="JSON file for runtime summary payload")
    parser.add_argument("--watch-payload", help="JSON file for watch summary payload")
    parser.add_argument("--strict-pending", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    runtime_payload = args.runtime_payload or os.environ.get("AXON_WATCH_RUNTIME_SUMMARY_PAYLOAD")
    watch_payload = args.watch_payload or os.environ.get("AXON_WATCH_WATCH_SUMMARY_PAYLOAD")
    results = run_check(
        runtime_payload=Path(runtime_payload) if runtime_payload else None,
        watch_payload=Path(watch_payload) if watch_payload else None,
        strict_pending=args.strict_pending,
    )
    return emit_many(results)


if __name__ == "__main__":
    raise SystemExit(main())
