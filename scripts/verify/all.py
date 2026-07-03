from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.verify.check_adr_governance import run_check as run_adr_check
from scripts.verify.check_dependency_directions import run_check as run_dependency_check
from scripts.verify.check_dto_sizes import run_check as run_dto_size_check
from scripts.verify.check_latency_budget import run_check as run_latency_check
from scripts.verify.common import CheckResult, emit_many


def _path_from_env(name: str) -> Path | None:
    value = os.environ.get(name)
    return Path(value) if value else None


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Axon-Watch verification scaffold.")
    parser.add_argument("--strict-pending", action="store_true")
    parser.add_argument("--runtime-payload")
    parser.add_argument("--watch-payload")
    parser.add_argument("--shell-boot-report")
    parser.add_argument("--runtime-latency-samples")
    parser.add_argument("--watch-latency-samples")
    parser.add_argument("--runtime-summary-url")
    parser.add_argument("--watch-summary-url")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    results: list[CheckResult] = []

    results.extend(run_dependency_check(strict_pending=args.strict_pending))
    results.extend(run_adr_check(strict_pending=args.strict_pending))

    results.extend(
        run_dto_size_check(
            runtime_payload=Path(args.runtime_payload) if args.runtime_payload else _path_from_env("AXON_WATCH_RUNTIME_SUMMARY_PAYLOAD"),
            watch_payload=Path(args.watch_payload) if args.watch_payload else _path_from_env("AXON_WATCH_WATCH_SUMMARY_PAYLOAD"),
            strict_pending=args.strict_pending,
        )
    )

    results.append(
        run_latency_check(
            "shell_boot_readiness",
            samples_file=Path(args.shell_boot_report) if args.shell_boot_report else _path_from_env("AXON_WATCH_SHELL_BOOT_REPORT"),
            strict_pending=args.strict_pending,
        )
    )
    results.append(
        run_latency_check(
            "runtime_summary_latency",
            samples_file=Path(args.runtime_latency_samples) if args.runtime_latency_samples else None,
            url=args.runtime_summary_url or os.environ.get("AXON_WATCH_RUNTIME_SUMMARY_URL"),
            strict_pending=args.strict_pending,
        )
    )
    results.append(
        run_latency_check(
            "watch_summary_latency",
            samples_file=Path(args.watch_latency_samples) if args.watch_latency_samples else None,
            url=args.watch_summary_url or os.environ.get("AXON_WATCH_WATCH_SUMMARY_URL"),
            strict_pending=args.strict_pending,
        )
    )

    return emit_many(results)


if __name__ == "__main__":
    raise SystemExit(main())
