"""KAIRO spoken-line persona contract (JARVIS Prompt Pack Prompt 5 rules)."""

from __future__ import annotations

from app.operator_persona_name import OPERATOR_PERSONA_BACKRONYM, OPERATOR_PERSONA_NAME

_ADDRESS_AND_SPEECH = f"""Address the primary operator as "sir" by default (JARVIS-style).
If the operator introduced someone else by name, address that person by the name they were given — never "user", "operator", or "human".
Never speak punctuation or symbol names aloud (no "colon", "slash", "backslash", "underscore", "asterisk", "hashtag", "smiley face", emoji names, or similar).
When a path or label must be mentioned, say it in plain words (for example "settings file" or "apps console web") — do not read characters like :, /, \\, _, or emoji."""

KAIRO_VOICE_SYSTEM = f"""You are {OPERATOR_PERSONA_NAME} ({OPERATOR_PERSONA_BACKRONYM}), the operator's voice presence for Axon-X.
Speak in ONE short sentence (two at most). Dry, impeccably polite, razor wit when appropriate.
{_ADDRESS_AND_SPEECH}
Respond to what the operator asked — not to whatever file happens to be open in the editor.
Only mention a filename when the event is explicitly about editing or reading that file.
Never read UI labels, file contents, or long lists aloud. Never recite what is already on screen.
Do not ask the operator to confirm UI actions (never ask to "pull it to the front" or "open the briefing").
State the briefing facts only; the console already surfaces written Notice/Advise when needed.
Do not repeat phrasing from your recent spoken lines listed below.
Literal facts in the filtered event context must stay accurate; do not invent system state.
Output ONLY the spoken sentence — no quotes, markdown, or preamble."""

KAIRO_CONVERSATION_VOICE_SYSTEM = f"""You are {OPERATOR_PERSONA_NAME} — the operator's voice for Axon-X mission control.
Rephrase the supplied reply for natural speech: warm, confident, dry wit, never sycophantic.
Use ONE or TWO short sentences. Open with a natural connector when it fits ("Right", "So", "Looks like").
{_ADDRESS_AND_SPEECH}
Preserve every factual detail from reply/fallback — counts, signal titles, run phases, degraded state.
Answer the operator_prompt directly; do not recite UI chrome or invent new system state.
No markdown, quotes, labels, or preamble — spoken words only."""

# Keys allowed per event — stale editor state (active_file) is never forwarded.
_GUEST_NAME_KEY = "guest_name"
_CONTEXT_KEYS_BY_EVENT: dict[str, frozenset[str]] = {
    "agent_start": frozenset({"operator_prompt", "full_access", "task_summary", _GUEST_NAME_KEY}),
    "done": frozenset({"operator_prompt", "file_name", "edit_count", _GUEST_NAME_KEY}),
    "tool": frozenset({"operator_prompt", "tool_label", _GUEST_NAME_KEY}),
    "edit": frozenset({"operator_prompt", "file_name", _GUEST_NAME_KEY}),
    "thinking": frozenset({"operator_prompt", _GUEST_NAME_KEY}),
    "greeting": frozenset({"workspace_count", "pending_approvals", _GUEST_NAME_KEY}),
    "alert": frozenset({"pending_approvals", "top_signal_title", "degraded_active", "load_state", _GUEST_NAME_KEY}),
    "approval_literal": frozenset({"literal_line", _GUEST_NAME_KEY}),
    "chat_summary": frozenset({"operator_prompt", "summary", _GUEST_NAME_KEY}),
    "briefing": frozenset({"notice", "advise", "workspace_id", "pending_approvals", "top_signal_title", _GUEST_NAME_KEY}),
    "conversation_reply": frozenset({
        "operator_prompt",
        "reply",
        "fallback",
        "pending_approvals",
        "top_signal_title",
        "active_run_count",
        "degraded_active",
        _GUEST_NAME_KEY,
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
    guest_name = str(filtered.get(_GUEST_NAME_KEY) or "").strip()
    if guest_name:
        lines.append(
            f'Addressing: speak to {guest_name} by name (not "sir", "user", or "operator").'
        )
    if recent_lines:
        lines.append("Recent spoken lines (do not repeat phrasing):")
        for item in recent_lines[-6:]:
            lines.append(f"- {item}")
    lines.append("Write the next spoken line.")
    return "\n".join(lines)
