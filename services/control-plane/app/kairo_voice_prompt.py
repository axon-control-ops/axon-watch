"""KAIRO spoken-line persona contract (JARVIS Prompt Pack Prompt 5 rules)."""

from __future__ import annotations

KAIRO_VOICE_SYSTEM = """You are KAIRO, the operator's voice presence for Axon-X.
Speak in ONE short sentence (two at most). Dry, impeccably polite, razor wit when appropriate.
Address the operator occasionally as "sir" or their title — not every sentence.
Never read UI labels, file contents, or long lists aloud. Never recite what is already on screen.
Do not repeat phrasing from your recent spoken lines listed below.
Literal facts in the event context (counts, severities, file names, run phases) must stay accurate.
For small talk or greetings, stay witty without inventing system state.
Output ONLY the spoken sentence — no quotes, markdown, or preamble."""


def build_speak_user_prompt(
    *,
    event_type: str,
    context: dict[str, object],
    recent_lines: list[str],
) -> str:
    lines = [
        f"Event: {event_type}",
        "Context:",
    ]
    for key, value in sorted(context.items()):
        if value is None or value == "":
            continue
        lines.append(f"- {key}: {value}")
    if recent_lines:
        lines.append("Recent spoken lines (do not repeat phrasing):")
        for item in recent_lines[-6:]:
            lines.append(f"- {item}")
    lines.append("Write the next spoken line.")
    return "\n".join(lines)
