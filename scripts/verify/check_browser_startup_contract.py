"""Validate browser-only startup contract and dedicated readiness docs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.verify.common import CheckResult, emit, load_json

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SPEC_PATH = REPO_ROOT / "config" / "browser-startup-contract.json"


def validate_browser_startup_contract(*, spec: dict[str, object] | None = None) -> CheckResult:
    spec = spec or load_json(DEFAULT_SPEC_PATH)

    for rel_path in spec.get("required_docs", []):
        if not (REPO_ROOT / str(rel_path)).is_file():
            return CheckResult(
                name="desktop_and_browser_startup",
                status="fail",
                message=f"missing startup doc: {rel_path}",
            )

    bootstrap_entry = REPO_ROOT / str(spec.get("bootstrap_entry", ""))
    if not bootstrap_entry.is_file():
        return CheckResult(
            name="desktop_and_browser_startup",
            status="fail",
            message=f"missing bootstrap entry: {spec.get('bootstrap_entry')}",
        )

    browser_doc = (REPO_ROOT / "docs/BROWSER_ONLY_STARTUP_CONTRACT.md").read_text(encoding="utf-8")
    if spec.get("desktop_deferral") and "desktop deferral" not in browser_doc.lower():
        return CheckResult(
            name="desktop_and_browser_startup",
            status="fail",
            message="browser startup contract must document desktop deferral",
        )

    boot_key = str(spec.get("console_boot_session_key", ""))
    app_vue = (REPO_ROOT / "apps/console-web/src/App.vue").read_text(encoding="utf-8")
    if boot_key not in app_vue:
        return CheckResult(
            name="desktop_and_browser_startup",
            status="fail",
            message="App.vue missing console boot session key",
        )

    readiness_endpoint = str(spec.get("readiness_endpoint", ""))
    control_plane_sources = [
        REPO_ROOT / "services/control-plane/app/main.py",
        REPO_ROOT / "services/control-plane/app/routes/health.py",
    ]
    readiness_found = any(
        path.is_file() and readiness_endpoint in path.read_text(encoding="utf-8")
        for path in control_plane_sources
    )
    if not readiness_found:
        return CheckResult(
            name="desktop_and_browser_startup",
            status="fail",
            message="control-plane missing readiness endpoint",
        )

    return CheckResult(
        name="desktop_and_browser_startup",
        status="pass",
        message="browser-only startup contract satisfied",
        details=[f"spec={DEFAULT_SPEC_PATH.relative_to(REPO_ROOT)}"],
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", help="browser startup contract path")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    spec_path = Path(args.spec) if args.spec else DEFAULT_SPEC_PATH
    spec = load_json(spec_path)
    return emit(validate_browser_startup_contract(spec=spec))


if __name__ == "__main__":
    raise SystemExit(main())
