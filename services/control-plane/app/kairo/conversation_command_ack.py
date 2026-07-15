"""Command acknowledgement lines for KAIRO voice conversation."""

from __future__ import annotations

from typing import Any

from app.chat.command_intent import (
    classify_command,
    command_display_name,
    command_requires_confirmation,
    expand_command_shortcuts,
    is_auto_complete_run_summary,
)


def workspace_short_label(pack: dict[str, Any]) -> str | None:
    workspace = pack.get("workspace")
    if not isinstance(workspace, dict):
        return None
    label = str(workspace.get("display_name") or workspace.get("workspace_id") or "").strip()
    return label or None


def command_ack_line(content: str, *, workspace_label: str | None = None) -> str:
    normalized = expand_command_shortcuts(content.strip())
    intent = classify_command(normalized)
    label = command_display_name(normalized)
    scope = f" for {workspace_label}" if workspace_label else ""
    auto_complete_hint = (
        " It should auto-complete once the output lands."
        if is_auto_complete_run_summary(label)
        else ""
    )
    if intent == "git_status":
        return (
            f"On it — running git status{scope}. "
            "I'll read branch and working tree, then put the full output in Command Results."
            f"{auto_complete_hint}"
        )
    if intent == "health_probe":
        return (
            f"Running a health probe{scope} now — "
            f"checking connectors, runtime, and service reachability.{auto_complete_hint}"
        )
    if intent == "list_files":
        return f"Listing workspace files{scope} — results will appear in Command Results.{auto_complete_hint}"
    if intent == "read_file":
        target = label.replace("Read ", "").strip()
        return (
            f"Opening {target or 'that file'} now — I'll surface the contents in Command Results."
            f"{auto_complete_hint}"
        )
    if intent == "shell_command":
        if command_requires_confirmation(normalized):
            return (
                f"I can run {label}{scope}. "
                "Say yes when you want me to dispatch it — output will land in Command Results."
            )
        return (
            f"On it — {label}{scope}. "
            f"Output will land in Command Results.{auto_complete_hint}"
        )
    if intent == "resume_from_review":
        return (
            "I can resume from review and pick up where we left off. "
            "Say yes when you want me to continue."
        )
    if intent == "move_voice_orb":
        from app.chat.move_voice_orb import move_voice_orb_ack, parse_move_voice_orb_ui_action

        action = parse_move_voice_orb_ui_action(normalized) or {
            "type": "move_voice_orb",
            "dock": "top-right",
        }
        return move_voice_orb_ack(action)
    if command_requires_confirmation(normalized):
        return (
            f"I can run {label}{scope}. "
            "Say yes when you want me to dispatch it — output will land in Command Results."
        )
    return f"Understood — {label}. I'll report back in Command Results."
