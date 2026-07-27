#!/usr/bin/env python3
"""Browser smoke: DashPro roster + deterministic REPORT (Lead→VAXON chain).

Requires a live console on :4173 and control-plane on :8787 (./scripts/dev/up.sh).
Prefer the project interpreter so Playwright drivers resolve:

  ./scripts/dev/python.sh scripts/verify/report-chain-browser-smoke.py

Writes screenshots + JSON under .local/verify/report-chain-smoke/.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = REPO_ROOT / ".local" / "verify" / "report-chain-smoke"


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


def _api_base_url() -> str:
    port = os.environ.get("AXON_WATCH_CONTROL_PLANE_PORT", "8787")
    return f"http://127.0.0.1:{port}"


def _operator_token() -> str:
    env_token = str(os.environ.get("AXON_WATCH_OPERATOR_TOKEN") or "").strip()
    if env_token:
        return env_token
    for candidate in (
        Path.home() / ".config" / "axon-watch" / "deployment.env",
        REPO_ROOT / ".local" / "deployment.env",
        REPO_ROOT / "config" / "deployment.env",
    ):
        if not candidate.is_file():
            continue
        for line in candidate.read_text(encoding="utf-8").splitlines():
            if line.startswith("AXON_WATCH_OPERATOR_TOKEN="):
                return line.split("=", 1)[1].strip().strip("\"'")
    return ""


def _request_json(
    url: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout: float = 60.0,
) -> dict[str, Any]:
    headers = {"Content-Type": "application/json"}
    token = _operator_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _get_json(url: str, timeout: float = 20.0) -> dict[str, Any]:
    return _request_json(url, method="GET", timeout=timeout)


def _post_json(url: str, payload: dict[str, Any], timeout: float = 60.0) -> dict[str, Any]:
    return _request_json(url, method="POST", payload=payload, timeout=timeout)

def _health(url: str) -> None:
    with urllib.request.urlopen(urllib.request.Request(url), timeout=10) as response:
        if response.status != 200:
            raise RuntimeError(f"{url} returned HTTP {response.status}")


def main() -> int:
    console = _console_base_url().rstrip("/")
    api = _api_base_url().rstrip("/")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    receipt: dict[str, Any] = {
        "started_at": _utc_now_iso(),
        "console": console,
        "api": api,
        "checks": [],
    }

    try:
        _health(f"{console}/")
        _health(f"{api}/api/health")
    except Exception as exc:  # noqa: BLE001
        print(f"Stack not ready: {exc}", file=sys.stderr)
        return 2

    # API: deterministic REPORT mentions Priya Lead rollup from verified receipt.
    report = _post_json(
        f"{api}/api/kairo/converse",
        {
            "content": "REPORT",
            "session_id": f"report-chain-smoke-{int(time.time())}",
            "workspace_id": "workspace_dashpro",
            "use_runtime": False,
            "answer_tier": "fast",
        },
    )
    reply = str(report.get("reply") or "")
    lane = str(report.get("dispatch_lane") or "")
    api_ok = (
        lane == "deterministic_report"
        and "Priya" in reply
        and ("Lead rollup" in reply or "Lead next" in reply or "graduation" in reply.lower())
    )
    receipt["checks"].append(
        {
            "id": "api_report_lane",
            "ok": api_ok,
            "dispatch_lane": lane,
            "reply_excerpt": reply[:500],
        }
    )
    (OUTPUT_DIR / "report-reply.json").write_text(
        json.dumps(report, indent=2)[:20000],
        encoding="utf-8",
    )

    # Roster: Priya must not show a fake "Run completed" failure line.
    roster = _get_json(f"{api}/api/workspaces/workspace_dashpro/company")
    employees = roster.get("employees") if isinstance(roster, dict) else None
    if not isinstance(employees, list):
        employees = (roster.get("company") or {}).get("employees") if isinstance(roster, dict) else []
    priya = next(
        (
            row
            for row in (employees or [])
            if isinstance(row, dict) and str(row.get("name") or "").strip() == "Priya"
        ),
        None,
    )
    detail = str((priya or {}).get("last_outcome_detail") or "").strip().lower()
    fake_success_failure = (
        str((priya or {}).get("last_outcome") or "").lower() == "failed"
        and detail in {"run completed", "completed", "success", "succeeded"}
    )
    receipt["checks"].append(
        {
            "id": "priya_roster_not_fake_success_failure",
            "ok": priya is not None and not fake_success_failure,
            "priya": {
                "status": (priya or {}).get("status"),
                "last_outcome": (priya or {}).get("last_outcome"),
                "last_outcome_detail": (priya or {}).get("last_outcome_detail"),
                "last_run_id": (priya or {}).get("last_run_id"),
            },
        }
    )

    # Browser: open DashPro IDE and capture Mission Control / Transmission if available.
    browser_ok = False
    browser_error = None
    try:
        from playwright.sync_api import sync_playwright

        headed = os.environ.get("AXON_HEADED", "").strip() in {"1", "true", "yes"}
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=not headed)
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.add_init_script(
                "sessionStorage.setItem('axon-x-boot-complete', '1');"
                "sessionStorage.setItem('axon.operator.center-view', 'grid');"
            )
            page.goto(console, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(2500)
            page.screenshot(path=str(OUTPUT_DIR / "01-mission-control.png"), full_page=True)

            # Prefer opening DashPro workspace into IDE when the control is present.
            for label in ("Open DashPro workspace", "DashPro", "workspace_dashpro"):
                locator = page.get_by_text(label, exact=False).first
                try:
                    if locator.count() and locator.is_visible():
                        locator.click(timeout=3000)
                        page.wait_for_timeout(2000)
                        break
                except Exception:
                    continue

            page.screenshot(path=str(OUTPUT_DIR / "02-after-dashpro-focus.png"), full_page=True)

            # Type REPORT into a visible talk/composer box if present.
            filled = False
            for selector in (
                "textarea",
                "input[type='text']",
                "[contenteditable='true']",
            ):
                boxes = page.locator(selector)
                for index in range(min(boxes.count(), 6)):
                    box = boxes.nth(index)
                    try:
                        if not box.is_visible():
                            continue
                        box.click(timeout=2000)
                        box.fill("REPORT")
                        box.press("Enter")
                        filled = True
                        break
                    except Exception:
                        continue
                if filled:
                    break

            page.wait_for_timeout(4000)
            page.screenshot(path=str(OUTPUT_DIR / "03-after-report.png"), full_page=True)
            body_text = page.inner_text("body")
            browser_ok = "Priya" in body_text or "Lead" in body_text or "stand-up" in body_text.lower()
            browser.close()
    except Exception as exc:  # noqa: BLE001
        browser_error = str(exc)
        browser_ok = False

    receipt["checks"].append(
        {
            "id": "browser_dashpro_report",
            "ok": browser_ok,
            "error": browser_error,
            "screenshots": [
                "01-mission-control.png",
                "02-after-dashpro-focus.png",
                "03-after-report.png",
            ],
        }
    )

    receipt["finished_at"] = _utc_now_iso()
    receipt["ok"] = all(bool(item.get("ok")) for item in receipt["checks"])
    (OUTPUT_DIR / "receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(json.dumps(receipt, indent=2))
    return 0 if receipt["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
