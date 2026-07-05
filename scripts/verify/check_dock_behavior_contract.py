"""Validate agent dock behavior contract files and wiring."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.verify.common import CheckResult, emit, load_json

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SPEC_PATH = REPO_ROOT / "config" / "dock-behavior-contract.json"


def validate_dock_behavior_contract(*, spec: dict[str, object] | None = None) -> CheckResult:
    spec = spec or load_json(DEFAULT_SPEC_PATH)

    for rel_path in spec.get("required_shell_files", []):
        if not (REPO_ROOT / str(rel_path)).is_file():
            return CheckResult(
                name="dock_behavior",
                status="fail",
                message=f"missing shell file: {rel_path}",
            )

    for rel_path in spec.get("required_pref_modules", []):
        if not (REPO_ROOT / str(rel_path)).is_file():
            return CheckResult(
                name="dock_behavior",
                status="fail",
                message=f"missing pref module: {rel_path}",
            )

    right_dock = (REPO_ROOT / "apps/console-web/src/components/shell/RightDock.vue").read_text(
        encoding="utf-8"
    )
    agent_dock = (REPO_ROOT / "apps/console-web/src/components/ide/AgentDock.vue").read_text(
        encoding="utf-8"
    )
    markers = spec.get("operator_mode_markers", {})
    for component in markers.get("right_dock_components", []):
        if str(component) not in right_dock:
            return CheckResult(
                name="dock_behavior",
                status="fail",
                message=f"RightDock missing operator component: {component}",
            )
    if str(markers.get("ide_dock_component", "")) not in agent_dock:
        return CheckResult(
            name="dock_behavior",
            status="fail",
            message="AgentDock missing IDE dock component wiring",
        )

    prefs = (REPO_ROOT / "apps/console-web/src/lib/ide-layout-prefs.ts").read_text(encoding="utf-8")
    collapsed_key = str(spec.get("agent_dock_collapsed_storage_key", ""))
    layout_key = str(spec.get("layout_mode_storage_key", ""))
    if collapsed_key not in prefs or layout_key not in prefs:
        return CheckResult(
            name="dock_behavior",
            status="fail",
            message="ide-layout-prefs missing dock storage keys",
        )

    return CheckResult(
        name="dock_behavior",
        status="pass",
        message="dock behavior contract satisfied",
        details=[f"spec={DEFAULT_SPEC_PATH.relative_to(REPO_ROOT)}"],
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", help="dock behavior contract path")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    spec_path = Path(args.spec) if args.spec else DEFAULT_SPEC_PATH
    spec = load_json(spec_path)
    return emit(validate_dock_behavior_contract(spec=spec))


if __name__ == "__main__":
    raise SystemExit(main())
