"""KAIRO spoken-line persona contract (JARVIS Prompt Pack Prompt 5 rules)."""

from __future__ import annotations

KAIRO_VOICE_SYSTEM = """You are KAIRO, the operator's voice presence for Axon-X.
Speak in ONE short sentence (two at most). Dry, impeccably polite, razor wit when appropriate.
Do NOT use "sir", "madam", or honorifics unless the operator used one in operator_prompt.
Respond to what the operator asked — not to whatever file happens to be open in the editor.
Only mention a filename when the event is explicitly about editing or reading that file.
Never read UI labels, file contents, or long lists aloud. Never recite what is already on screen.
Do not repeat phrasing from your recent spoken lines listed below.
Literal facts in the filtered event context must stay accurate; do not invent system state.
Output ONLY the spoken sentence — no quotes, markdown, or preamble."""

# Keys allowed per event — stale editor state (active_file) is never forwarded.
_CONTEXT_KEYS_BY_EVENT: dict[str, frozenset[str]] = {
    "agent_start": frozenset({"operator_prompt", "full_access", "task_summary"}),
    "done": frozenset({"operator_prompt", "file_name", "edit_count"}),
    "tool": frozenset({"operator_prompt", "tool_label"}),
    "edit": frozenset({"operator_prompt", "file_name"}),
    "thinking": frozenset({"operator_prompt"}),
    "greeting": frozenset({"workspace_count", "pending_approvals"}),
    "alert": frozenset({"pending_approvals", "top_signal_title", "degraded_active", "load_state"}),
    "approval_literal": frozenset({"literal_line"}),
    "chat_summary": frozenset({"operator_prompt", "summary"}),
    "briefing": frozenset({"notice", "advise", "workspace_id", "pending_approvals", "top_signal_title"}),
    "conversation_reply": frozenset({
        "operator_prompt",
        "reply",
        "fallback",
        "pending_approvals",
        "top_signal_title",
        "active_run_count",
        "degraded_active",
    }),
}


def filter_speak_context(event_type: str, context: dict[str, object]) -> dict[str, object]:
    allowed = _CONTEXT_KEYS_BY_EVENT.get(event_type)
    if allowed is None:
        return {
            key: value
            for key, value in context.items()
            if key != "active_file" and value is not None and value != ""
        }
    return {
        key: value
        for key, value in context.items()
        if key in allowed and value is not None and value != ""
    }


def build_speak_user_prompt(
    *,
    event_type: str,
    context: dict[str, object],
    recent_lines: list[str],
) -> str:
    filtered = filter_speak_context(event_type, context)
    lines = [
        f"Event: {event_type}",
        "Context:",
    ]
    if filtered:
        for key, value in sorted(filtered.items()):
            lines.append(f"- {key}: {value}")
    else:
        lines.append("- (none)")
    if recent_lines:
        lines.append("Recent spoken lines (do not repeat phrasing):")
        for item in recent_lines[-6:]:
            lines.append(f"- {item}")
    lines.append("Write the next spoken line.")
    return "\n".join(lines)
