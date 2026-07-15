"""Parse move-voice-orb operator / voice commands into UI actions."""

from __future__ import annotations

import re
from typing import Any

_MOVE_ORB_RE = re.compile(
    r"\b(?:put|move|place|send|dock)\b.{0,40}\b(?:orb|voice\s*orb|jarvis|vaxon)\b"
    r"|\b(?:orb|voice\s*orb)\b.{0,40}\b(?:to|at|on)\b"
    r"|\bdodge\b.{0,20}\b(?:orb|voice\s*orb)\b"
    r"|\b(?:orb|voice\s*orb)\b.{0,20}\bdodge\b",
    re.IGNORECASE,
)

_DOCK_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\btop[\s\-]?left\b|\bupper[\s\-]?left\b", re.IGNORECASE), "top-left"),
    (re.compile(r"\btop[\s\-]?right\b|\bupper[\s\-]?right\b", re.IGNORECASE), "top-right"),
    (re.compile(r"\bbottom[\s\-]?left\b|\blower[\s\-]?left\b", re.IGNORECASE), "bottom-left"),
    (re.compile(r"\bbottom[\s\-]?right\b|\blower[\s\-]?right\b", re.IGNORECASE), "bottom-right"),
    (re.compile(r"\bcenter\b|\bmiddle\b", re.IGNORECASE), "center"),
)

_SMART_DODGE_RE = re.compile(
    r"\b(?:smart[\s\-]?dodge|auto[\s\-]?dodge|dodge|get\s+out\s+of\s+the\s+way)\b",
    re.IGNORECASE,
)


def is_move_voice_orb_command(content: str) -> bool:
    return bool(_MOVE_ORB_RE.search(content.strip()))


def parse_move_voice_orb_ui_action(content: str) -> dict[str, Any] | None:
    trimmed = content.strip()
    if not trimmed or not is_move_voice_orb_command(trimmed):
        return None
    if _SMART_DODGE_RE.search(trimmed) and not any(p.search(trimmed) for p, _ in _DOCK_PATTERNS):
        return {"type": "move_voice_orb", "mode": "smart_dodge"}
    for pattern, dock in _DOCK_PATTERNS:
        if pattern.search(trimmed):
            return {"type": "move_voice_orb", "dock": dock}
    if _SMART_DODGE_RE.search(trimmed):
        return {"type": "move_voice_orb", "mode": "smart_dodge"}
    # Default dock when "move the orb" without a corner.
    return {"type": "move_voice_orb", "dock": "top-right"}


def move_voice_orb_ack(ui_action: dict[str, Any]) -> str:
    if ui_action.get("mode") == "smart_dodge":
        return "Moving the voice orb out of the way."
    dock = str(ui_action.get("dock") or "top-right").replace("-", " ")
    return f"Moving the voice orb to {dock}."
