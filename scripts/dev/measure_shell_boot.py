#!/usr/bin/env python3
"""Measure console shell boot readiness for the nightly verify gate."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path


def _utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _fetch(url: str, timeout_seconds: float) -> None:
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        response.read()


def measure_bootstrap_critical_path(
    *,
    console_base_url: str,
    control_plane_base_url: str,
    timeout_seconds: float,
) -> dict[str, object]:
    """Proxy shell boot: index fetch + parallel bootstrap API calls from loadBootstrapData()."""
    console_base = console_base_url.rstrip("/")
    control_base = control_plane_base_url.rstrip("/")
    bootstrap_urls = [
        f"{control_base}/api/runtime/summary",
        f"{control_base}/api/inbox",
        f"{control_base}/api/briefing",
        f"{control_base}/api/workspaces",
        f"{control_base}/api/runs",
    ]

    started = time.perf_counter()
    index_request = urllib.request.Request(f"{console_base}/")
    with urllib.request.urlopen(index_request, timeout=timeout_seconds) as response:
        response.read()

    with ThreadPoolExecutor(max_workers=len(bootstrap_urls)) as pool:
        futures = [
            pool.submit(_fetch, url, timeout_seconds)
            for url in bootstrap_urls
        ]
        for future in as_completed(futures):
            future.result()

    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    return {
        "shell_ready_ms": elapsed_ms,
        "source": "bootstrap-critical-path",
        "generated_at": _utc_now_iso(),
        "console_base_url": console_base,
        "control_plane_base_url": control_base,
        "bootstrap_routes": [url.removeprefix(control_base) for url in bootstrap_urls],
        "note": "Index fetch plus parallel bootstrap API calls mirroring shell.loadBootstrapData().",
    }


def measure_browser_boot(
    *,
    console_base_url: str,
    timeout_seconds: float,
) -> dict[str, object]:
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    from playwright.sync_api import sync_playwright

    console_base = console_base_url.rstrip("/")
    started = time.perf_counter()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            context = browser.new_context()
            context.add_init_script(
                "sessionStorage.setItem('axon-x-boot-complete', '1');"
            )
            page = context.new_page()
            page.goto(console_base, wait_until="domcontentloaded", timeout=int(timeout_seconds * 1000))
            page.wait_for_selector(".console-shell--mockup", timeout=int(timeout_seconds * 1000))
            page.wait_for_selector(".region-status-bar", timeout=int(timeout_seconds * 1000))
            page.wait_for_function(
                """() => {
                  const bar = document.querySelector('.region-status-bar');
                  return Boolean(bar && bar.textContent && bar.textContent.trim().length > 0);
                }""",
                timeout=int(timeout_seconds * 1000),
            )
        except PlaywrightTimeoutError as exc:
            raise RuntimeError(f"browser shell boot timed out: {exc}") from exc
        finally:
            browser.close()

    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    return {
        "shell_ready_ms": elapsed_ms,
        "source": "playwright-chromium",
        "generated_at": _utc_now_iso(),
        "console_base_url": console_base,
        "note": "Headless Chromium with boot overlay skipped via sessionStorage init script.",
    }


def _playwright_usable() -> bool:
    """Probe Playwright in a subprocess so broken system installs do not leak async noise."""
    try:
        import playwright  # noqa: F401
    except ImportError:
        return False

    probe_script = """
import sys
try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        browser.close()
    sys.exit(0)
except Exception:
    sys.exit(1)
"""
    result = subprocess.run(
        [sys.executable, "-c", probe_script],
        capture_output=True,
        timeout=15,
        check=False,
    )
    return result.returncode == 0


def measure_shell_boot(
    *,
    console_base_url: str,
    control_plane_base_url: str,
    mode: str,
    timeout_seconds: float,
) -> dict[str, object]:
    if mode == "browser":
        return measure_browser_boot(
            console_base_url=console_base_url,
            timeout_seconds=timeout_seconds,
        )
    if mode == "auto":
        if _playwright_usable():
            try:
                return measure_browser_boot(
                    console_base_url=console_base_url,
                    timeout_seconds=timeout_seconds,
                )
            except (ImportError, RuntimeError, OSError, AttributeError):
                pass
        return measure_bootstrap_critical_path(
            console_base_url=console_base_url,
            control_plane_base_url=control_plane_base_url,
            timeout_seconds=timeout_seconds,
        )
    return measure_bootstrap_critical_path(
        console_base_url=console_base_url,
        control_plane_base_url=control_plane_base_url,
        timeout_seconds=timeout_seconds,
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--console-base-url",
        default="http://127.0.0.1:4173",
        help="console-web base URL",
    )
    parser.add_argument(
        "--control-plane-base-url",
        default="http://127.0.0.1:8787",
        help="control-plane base URL",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(".local/verify/shell-boot-report.json"),
        help="JSON report output path",
    )
    parser.add_argument(
        "--mode",
        choices=("auto", "browser", "bootstrap"),
        default="auto",
        help="auto prefers Playwright when installed, else bootstrap critical path",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=8.0,
        help="per-step timeout",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        payload = measure_shell_boot(
            console_base_url=args.console_base_url,
            control_plane_base_url=args.control_plane_base_url,
            mode=args.mode,
            timeout_seconds=args.timeout_seconds,
        )
    except (OSError, urllib.error.URLError, RuntimeError) as exc:
        print(f"shell boot measurement failed: {exc}", file=sys.stderr)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"shell_ready_ms={payload['shell_ready_ms']} source={payload['source']}")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
