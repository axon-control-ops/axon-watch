from __future__ import annotations

import argparse
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.verify.common import CheckResult, emit, load_config, load_json, percentile_95


ENV_BY_BUDGET = {
    "shell_boot_readiness": "AXON_WATCH_SHELL_BOOT_REPORT",
    "runtime_summary_latency": "AXON_WATCH_RUNTIME_SUMMARY_URL",
    "watch_summary_latency": "AXON_WATCH_WATCH_SUMMARY_URL",
}


def _load_samples_from_file(budget_name: str, path: Path) -> list[float]:
    payload = load_json(path)
    if isinstance(payload, list):
        return [float(sample) for sample in payload]
    if isinstance(payload, dict):
        if "samples_ms" in payload:
            return [float(sample) for sample in payload["samples_ms"]]
        if budget_name == "shell_boot_readiness" and "shell_ready_ms" in payload:
            return [float(payload["shell_ready_ms"])]
    raise ValueError(
        "expected JSON array, {'samples_ms': [...]}, or "
        "{'shell_ready_ms': number} for shell boot readiness"
    )


def _collect_live_samples(url: str, request_count: int, timeout_ms: int) -> list[float]:
    samples: list[float] = []
    timeout_seconds = timeout_ms / 1000
    for _ in range(request_count):
        started = time.perf_counter()
        with urllib.request.urlopen(url, timeout=timeout_seconds) as response:
            response.read()
        samples.append((time.perf_counter() - started) * 1000)
    return samples


def run_check(
    budget_name: str,
    samples_file: Path | None = None,
    url: str | None = None,
    request_count: int = 15,
    timeout_ms: int = 2000,
    strict_pending: bool = False,
) -> CheckResult:
    budgets = load_config()["budgets"]
    budget = budgets[budget_name]
    threshold_ms = float(budget["threshold_ms"])

    try:
        if samples_file is not None:
            samples = _load_samples_from_file(budget_name, samples_file)
            source = f"file {samples_file}"
        elif url:
            if budget_name == "shell_boot_readiness":
                raise ValueError("shell boot readiness requires a report file, not a URL")
            samples = _collect_live_samples(url, request_count=request_count, timeout_ms=timeout_ms)
            source = f"live URL {url}"
        else:
            status = "fail" if strict_pending else "pending"
            return CheckResult(
                name=budget_name,
                status=status,
                message="no timing evidence supplied yet",
                details=[
                    f"threshold={threshold_ms:.0f}ms gate={budget['gate']} owner={budget['owner']}",
                    "future slice must provide either a report file or a live URL",
                ],
            )

        p95_ms = percentile_95(samples)
        if p95_ms <= threshold_ms:
            return CheckResult(
                name=budget_name,
                status="pass",
                message=f"p95 {p95_ms:.1f}ms <= {threshold_ms:.0f}ms",
                details=[f"source={source}", f"samples={len(samples)}"],
            )
        return CheckResult(
            name=budget_name,
            status="fail",
            message=f"p95 {p95_ms:.1f}ms > {threshold_ms:.0f}ms",
            details=[f"source={source}", f"samples={len(samples)}"],
        )
    except (OSError, urllib.error.URLError, ValueError) as exc:
        return CheckResult(name=budget_name, status="fail", message=str(exc))


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check an Axon-Watch latency budget.")
    parser.add_argument(
        "budget_name",
        choices=sorted(ENV_BY_BUDGET),
        help="budget to check",
    )
    parser.add_argument(
        "--samples-file",
        help="JSON timing report path; supports arrays, {'samples_ms': [...]}, or shell_ready_ms",
    )
    parser.add_argument("--url", help="live URL to measure for route latency budgets")
    parser.add_argument("--request-count", type=int, default=15)
    parser.add_argument("--timeout-ms", type=int, default=2000)
    parser.add_argument("--strict-pending", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    env_key = ENV_BY_BUDGET[args.budget_name]
    env_value = os.environ.get(env_key)
    samples_file = Path(args.samples_file) if args.samples_file else None
    url = args.url
    if samples_file is None and env_value and args.budget_name == "shell_boot_readiness":
        samples_file = Path(env_value)
    if url is None and env_value and args.budget_name != "shell_boot_readiness":
        url = env_value
    result = run_check(
        args.budget_name,
        samples_file=samples_file,
        url=url,
        request_count=args.request_count,
        timeout_ms=args.timeout_ms,
        strict_pending=args.strict_pending,
    )
    return emit(result)


if __name__ == "__main__":
    raise SystemExit(main())
