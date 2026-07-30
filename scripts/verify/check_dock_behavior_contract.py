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

    for rel_path in spec.get("required_voice_modules", []):
        if not (REPO_ROOT / str(rel_path)).is_file():
            return CheckResult(
                name="dock_behavior",
                status="fail",
                message=f"missing voice module: {rel_path}",
            )

    right_dock = (REPO_ROOT / "apps/console-web/src/components/shell/RightDock.vue").read_text(
        encoding="utf-8"
    )
    agent_dock = (REPO_ROOT / "apps/console-web/src/components/ide/AgentDock.vue").read_text(
        encoding="utf-8"
    )
    conversation_seam = (
        REPO_ROOT / "apps/console-web/src/components/ConversationSeamPanel.vue"
    ).read_text(encoding="utf-8")
    sticky_prompt_css = (
        REPO_ROOT
        / "apps/console-web/src/components/ide/agent-dock/agent-dock-sticky-prompt.css"
    ).read_text(encoding="utf-8")
    app_vue = (REPO_ROOT / "apps/console-web/src/App.vue").read_text(encoding="utf-8")

    operator_markers = spec.get("operator_mode_markers", {})
    for component in operator_markers.get("right_dock_components", []):
        if str(component) not in right_dock:
            return CheckResult(
                name="dock_behavior",
                status="fail",
                message=f"RightDock missing operator component: {component}",
            )
    if operator_markers.get("thread_seam_collapsible") and "toggleDockSeam('thread')" not in right_dock:
        return CheckResult(
            name="dock_behavior",
            status="fail",
            message="RightDock thread seam is not collapsible",
        )

    ide_markers = spec.get("ide_dock_markers", {})
    if str(ide_markers.get("ide_dock_component", "")) not in agent_dock:
        return CheckResult(
            name="dock_behavior",
            status="fail",
            message="AgentDock missing IDE dock component wiring",
        )
    thread_meta = str(ide_markers.get("thread_section_meta", ""))
    if thread_meta and thread_meta not in agent_dock:
        return CheckResult(
            name="dock_behavior",
            status="fail",
            message=f"AgentDock missing thread section meta marker: {thread_meta}",
        )
    for marker in (
        "conversation-seam__operator-turn",
        "show-resend",
    ):
        if marker not in conversation_seam:
            return CheckResult(
                name="dock_behavior",
                status="fail",
                message=f"AgentDock operator message missing action marker: {marker}",
            )
    for marker in (
        "@media (hover: hover) and (pointer: fine)",
        ".agent-dock-sticky-prompt:hover",
        ".agent-dock-sticky-prompt--active",
        ".conversation-seam__operator-turn:hover",
        ".conversation-seam__operator-turn:focus-within",
        "opacity: 0",
    ):
        if marker not in sticky_prompt_css:
            return CheckResult(
                name="dock_behavior",
                status="fail",
                message=f"AgentDock operator hover actions missing CSS marker: {marker}",
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

    hero_prefs = (REPO_ROOT / "apps/console-web/src/lib/dock-hero-prefs.ts").read_text(
        encoding="utf-8"
    )
    hero_key = str(spec.get("dock_hero_mode_storage_key", ""))
    if hero_key and hero_key not in hero_prefs:
        return CheckResult(
            name="dock_behavior",
            status="fail",
            message="dock-hero-prefs missing hero mode storage key",
        )

    if "MobileVoiceCockpitStrip" not in app_vue:
        return CheckResult(
            name="dock_behavior",
            status="fail",
            message="App.vue missing mobile voice cockpit strip wiring",
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
