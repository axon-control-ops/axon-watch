#!/usr/bin/env python3
"""Headed browser smoke checks for Axon-X operator console (:4173).

Runs Playwright checks against a live dev stack. Use AXON_HEADED=1 for a visible
browser window; default is headless with screenshots saved under .local/verify/.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


def _utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _console_base_url() -> str:
    port = os.environ.get("AXON_WATCH_CONSOLE_WEB_PORT", "4173")
    return f"http://127.0.0.1:{port}"


def _health_ok(console_base_url: str, timeout_seconds: float) -> None:
    request = urllib.request.Request(f"{console_base_url.rstrip('/')}/")
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        if response.status != 200:
            raise RuntimeError(f"console index returned HTTP {response.status}")


def _playwright_usable() -> bool:
    try:
        import playwright  # noqa: F401
    except ImportError:
        return False
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            browser.close()
        return True
    except Exception:
        return False


def _boot_init_script() -> str:
    return """
sessionStorage.setItem('axon-x-boot-complete', '1');
sessionStorage.setItem('axon.operator.center-view', 'grid');
"""


def _css_bundle_ok(console_base_url: str, timeout_seconds: float) -> None:
    css_url = f"{console_base_url.rstrip('/')}/src/styles/app.css"
    request = urllib.request.Request(css_url)
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            if response.status != 200:
                raise RuntimeError(f"console css returned HTTP {response.status}")
            body = response.read(512).decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        raise RuntimeError(
            "console css failed to compile; restart ./scripts/dev/up.sh --no-open "
            f"({css_url} returned HTTP {exc.code})",
        ) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"console css probe failed for {css_url}: {exc}") from exc

    if body.lstrip().startswith("<!DOCTYPE") or "Internal Server Error" in body:
        raise RuntimeError(
            "console css failed to compile; restart ./scripts/dev/up.sh --no-open "
            f"({css_url} returned an HTML error page)",
        )


def _run_browser_checks(
    *,
    console_base_url: str,
    headed: bool,
    timeout_seconds: float,
    output_dir: Path,
) -> dict[str, Any]:
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    from playwright.sync_api import sync_playwright

    output_dir.mkdir(parents=True, exist_ok=True)
    checks: list[dict[str, Any]] = []
    started = time.perf_counter()

    def record(step: str, ok: bool, detail: str = "") -> None:
        checks.append({"step": step, "ok": ok, "detail": detail})

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=not headed)
        try:
            context = browser.new_context(viewport={"width": 1440, "height": 900})
            context.add_init_script(_boot_init_script())
            page = context.new_page()
            timeout_ms = int(timeout_seconds * 1000)

            page.goto(
                console_base_url.rstrip("/"),
                wait_until="domcontentloaded",
                timeout=timeout_ms,
            )
            page.wait_for_selector(".console-shell--mockup", timeout=timeout_ms)
            page.wait_for_selector(".region-status-bar", timeout=timeout_ms)
            page.wait_for_function(
                """() => {
                  const bar = document.querySelector('.region-status-bar');
                  return Boolean(bar && bar.textContent && bar.textContent.trim().length > 0);
                }""",
                timeout=timeout_ms,
            )
            record("shell_boot", True, "console shell and status bar rendered")
            page.screenshot(path=str(output_dir / "01-shell-boot.png"), full_page=False)

            layout_group = page.get_by_role("group", name="Layout mode")
            layout_group.wait_for(timeout=timeout_ms)
            record("layout_toggle", True, "operator/IDE layout toggle visible")

            layout_group.get_by_role("button", name="OPERATOR", exact=True).click()
            page.wait_for_selector(".console-shell--operator", timeout=timeout_ms)
            page.wait_for_selector(".conversation-seam", timeout=timeout_ms)
            record("operator_mode", True, "operator layout and conversation seam visible")
            page.screenshot(path=str(output_dir / "02-operator-mode.png"), full_page=False)

            layout_group.get_by_role("button", name="IDE", exact=True).click()
            page.wait_for_selector(".console-shell--ide", timeout=timeout_ms)
            page.wait_for_selector(".agent-dock-composer", timeout=timeout_ms)
            page.get_by_label("Agent composer").wait_for(timeout=timeout_ms)
            record("ide_mode", True, "IDE layout and agent composer visible")
            page.screenshot(path=str(output_dir / "03-ide-mode.png"), full_page=False)

            layout_group.get_by_role("button", name="OPERATOR", exact=True).click()
            page.wait_for_selector(".console-shell--operator", timeout=timeout_ms)
            command_input = page.locator(
                'textarea[aria-label="Operator command"], input[aria-label="Operator command"]'
            )
            try:
                command_input.first.wait_for(timeout=timeout_ms)
                record("operator_command", True, "operator command input visible")
            except PlaywrightTimeoutError:
                record(
                    "operator_command",
                    False,
                    "operator command input not found (dock hero may be collapsed)",
                )

            page.screenshot(path=str(output_dir / "04-operator-command.png"), full_page=False)

            failed = [item for item in checks if not item["ok"]]
            if failed:
                names = ", ".join(item["step"] for item in failed)
                raise RuntimeError(f"headed browser smoke failed: {names}")

        finally:
            browser.close()

    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    return {
        "schema_version": 1,
        "generated_at": _utc_now_iso(),
        "console_base_url": console_base_url.rstrip("/"),
        "headed": headed,
        "elapsed_ms": elapsed_ms,
        "checks": checks,
        "screenshots_dir": str(output_dir),
        "source": "playwright-chromium",
    }


def run_smoke(
    *,
    console_base_url: str | None = None,
    headed: bool | None = None,
    timeout_seconds: float = 30.0,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    base = (console_base_url or _console_base_url()).rstrip("/")
    use_headed = headed if headed is not None else os.environ.get("AXON_HEADED", "").strip() in {
        "1",
        "true",
        "yes",
    }
    artifact_dir = output_dir or (
        Path(__file__).resolve().parents[2] / ".local" / "verify" / "headed-smoke"
    )

    _health_ok(base, timeout_seconds)
    _css_bundle_ok(base, timeout_seconds)
    if not _playwright_usable():
        raise RuntimeError(
            "Playwright is unavailable. Install with: pip install playwright && playwright install chromium"
        )

    return _run_browser_checks(
        console_base_url=base,
        headed=use_headed,
        timeout_seconds=timeout_seconds,
        output_dir=artifact_dir,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Axon-X headed browser smoke checks")
    parser.add_argument(
        "--console-base-url",
        default=_console_base_url(),
        help="Console web base URL (default: http://127.0.0.1:4173)",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Open a visible browser window (default: headless + screenshots)",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=30.0,
        help="Per-step timeout in seconds",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for screenshots and report JSON",
    )
    parser.add_argument(
        "--write-report",
        type=Path,
        default=None,
        help="Write JSON report to this path",
    )
    args = parser.parse_args(argv)

    artifact_dir = args.output_dir or (
        Path(__file__).resolve().parents[2] / ".local" / "verify" / "headed-smoke"
    )
    report_path = args.write_report or artifact_dir / "headed-browser-smoke-report.json"

    try:
        payload = run_smoke(
            console_base_url=args.console_base_url,
            headed=args.headed,
            timeout_seconds=args.timeout_seconds,
            output_dir=artifact_dir,
        )
    except Exception as exc:
        print(f"HEADED-BROWSER-SMOKE FAIL: {exc}", file=sys.stderr)
        return 1

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"HEADED-BROWSER-SMOKE PASS ({payload['elapsed_ms']} ms)")
    print(f"Report: {report_path}")
    print(f"Screenshots: {payload['screenshots_dir']}")
    if payload.get("headed"):
        print("Mode: headed (visible browser)")
    else:
        print("Mode: headless (set AXON_HEADED=1 or --headed for visible browser)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
