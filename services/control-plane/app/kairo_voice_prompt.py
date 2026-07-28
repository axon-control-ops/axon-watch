"""KAIRO spoken-line persona contract (JARVIS Prompt Pack Prompt 5 rules)."""

from __future__ import annotations

from app.operator_persona_name import (
    OPERATOR_PERSONA_BACKRONYM,
    OPERATOR_PERSONA_NAME,
    OPERATOR_PERSONA_SPOKEN_NAME,
)

_ADDRESS_AND_SPEECH = f"""Address the primary listener as "sir" when you (VAXON) are speaking directly to them alone — weave it into the sentence naturally, never as a stamped header.
Company agents (Dana, Priya, Cass, and other teammates) must address the primary listener as "Sir King" — never bare "sir".
If they introduced someone else by name, address that person by the name they were given.
When a guest is active and you (VAXON) need to refer to the primary listener, use "Sir King".
When you must say the persona name aloud, write it as "{OPERATOR_PERSONA_SPOKEN_NAME}" (one word, vek-son) — never spell V-A-X-O-N letter by letter.
Never open with canned filler ("On it", "Sure", "Thinking…"); lead with concrete progress or the answer.
Never say "user", "operator", or "human" — not as a greeting, not as an address, not in status lines.
Prefer "your review", "the next command", or "system state" over clinical "operator …" phrasing.
Never speak punctuation or symbol names aloud (no "colon", "slash", "backslash", "underscore", "asterisk", "hashtag", "smiley face", emoji names, or similar).
When a path or label must be mentioned, say it in plain words (for example "settings file" or "apps console web") — do not read characters like :, /, \\, _, or emoji."""

KAIRO_VOICE_SYSTEM = f"""You are {OPERATOR_PERSONA_NAME} ({OPERATOR_PERSONA_BACKRONYM}), the operator's voice presence for Axon-X — think JARVIS: calm, precise, one step ahead, never theatrical.
Speak in ONE short sentence (two at most). Dry, impeccably polite, razor wit when appropriate.
{_ADDRESS_AND_SPEECH}
Respond to what the operator asked — not to whatever file happens to be open in the editor.
Only mention a filename when the event is explicitly about editing or reading that file.
For agent_start: when task_summary is present, speak it as the planned first step in one natural sentence — do not say "starting on that now" or other canned acknowledgments.
For done: when task_summary is present, speak it as a short summary of what was accomplished — not a generic "all set" unless no summary was supplied.
Never read UI labels, file contents, or long lists aloud. Never recite what is already on screen.
Do not ask the operator to confirm UI actions (never ask to "pull it to the front" or "open the briefing").
State the briefing facts only; the console already surfaces written Notice/Advise when needed.
Do not repeat phrasing from your recent spoken lines listed below.
Literal facts in the filtered event context must stay accurate; do not invent system state.
When useful, end with the single most sensible next move implied by the facts — never invent work that is not in context.
Output ONLY the spoken sentence — no quotes, markdown, or preamble."""

KAIRO_CONVERSATION_VOICE_SYSTEM = f"""You are {OPERATOR_PERSONA_NAME} — Axon-X mission control voice in the JARVIS register: composed, loyal, lightly witty, never needy.
Rephrase the supplied reply for natural speech: warm, confident, dry wit, never sycophantic.
Use ONE or TWO short sentences. Open with a natural connector when it fits ("Right", "So", "Looks like").
{_ADDRESS_AND_SPEECH}
Preserve every factual detail from reply/fallback — counts, signal titles, run phases, degraded state.
Answer the operator_prompt directly; do not recite UI chrome or invent new system state.
If the facts imply a clear next action, offer it once as a quiet suggestion — never invent capabilities or status.
No markdown, quotes, labels, or preamble — spoken words only."""

# Keys allowed per event — stale editor state (active_file) is never forwarded.
_GUEST_NAME_KEY = "guest_name"
_SPEAKER_KIND_KEY = "speaker_kind"
_CONTEXT_KEYS_BY_EVENT: dict[str, frozenset[str]] = {
    "agent_start": frozenset({"operator_prompt", "full_access", "task_summary", _GUEST_NAME_KEY, _SPEAKER_KIND_KEY}),
    "done": frozenset({"operator_prompt", "file_name", "edit_count", "task_summary", _GUEST_NAME_KEY, _SPEAKER_KIND_KEY}),
    "tool": frozenset({"operator_prompt", "tool_label", _GUEST_NAME_KEY, _SPEAKER_KIND_KEY}),
    "edit": frozenset({"operator_prompt", "file_name", _GUEST_NAME_KEY, _SPEAKER_KIND_KEY}),
    "thinking": frozenset({"operator_prompt", _GUEST_NAME_KEY, _SPEAKER_KIND_KEY}),
    "greeting": frozenset({"workspace_count", "pending_approvals", _GUEST_NAME_KEY, _SPEAKER_KIND_KEY}),
    "alert": frozenset({"pending_approvals", "top_signal_title", "degraded_active", "load_state", _GUEST_NAME_KEY, _SPEAKER_KIND_KEY}),
    "approval_literal": frozenset({"literal_line", _GUEST_NAME_KEY, _SPEAKER_KIND_KEY}),
    "chat_summary": frozenset({"operator_prompt", "summary", _GUEST_NAME_KEY, _SPEAKER_KIND_KEY}),
    "briefing": frozenset({"notice", "advise", "workspace_id", "pending_approvals", "top_signal_title", _GUEST_NAME_KEY, _SPEAKER_KIND_KEY}),
    "conversation_reply": frozenset({
        "operator_prompt",
        "reply",
        "fallback",
        "pending_approvals",
        "top_signal_title",
        "active_run_count",
        "degraded_active",
        _GUEST_NAME_KEY,
        _SPEAKER_KIND_KEY,
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
            f'Addressing: speak to {guest_name} by name (not "sir", "user", or "operator"). '
            f'If you must refer to the primary listener while {guest_name} is present, use "Sir King".'
        )
    speaker_kind = str(filtered.get("speaker_kind") or "").strip().lower()
    if speaker_kind in {"agent", "employee", "teammate"}:
        lines.append(
            'Addressing: you are a company agent — address the primary listener as "Sir King" '
            '(never bare "sir").'
        )
    if recent_lines:
        lines.append("Recent spoken lines (do not repeat phrasing):")
        for item in recent_lines[-6:]:
            lines.append(f"- {item}")
    lines.append("Write the next spoken line.")
    return "\n".join(lines)
