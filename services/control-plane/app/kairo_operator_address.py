"""Operator address forms — Sir King for the primary listener; guest name when introduced."""

from __future__ import annotations

import re

OPERATOR_ADDRESS_SHORT = "sir"
OPERATOR_ADDRESS_FULL = "Sir King"

_SIR_KING_RE = re.compile(r"\bsir\s+king\b", re.IGNORECASE)
_SIR_RE = re.compile(r"\bsir\b", re.IGNORECASE)


def normalize_speaker_kind(value: object) -> str:
    kind = str(value or "vaxon").strip().lower()
    if kind in {"agent", "employee", "teammate"}:
        return "agent"
    return "vaxon"


def apply_operator_address(
    text: str,
    guest_name: str | None = None,
    *,
    speaker_kind: str = "vaxon",
) -> str:
    """Apply Sir King / guest-name addressing rules.

    - Guest active: replace sir / Sir King with the guest name (utterance directed at them).
    - No guest: bare "sir" becomes "Sir King" for every speaker (VAXON and company agents).
    """
    cleaned = str(text or "")
    if not cleaned:
        return cleaned

    name = str(guest_name or "").strip()
    if name:
        cleaned = _SIR_KING_RE.sub(name, cleaned)
        cleaned = _SIR_RE.sub(name, cleaned)
        return cleaned

    # Avoid double-expanding "Sir King".
    placeholders: list[str] = []

    def _hold(match: re.Match[str]) -> str:
        placeholders.append(match.group(0))
        return f"\0ADDR{len(placeholders) - 1}\0"

    held = _SIR_KING_RE.sub(_hold, cleaned)
    held = _SIR_RE.sub(OPERATOR_ADDRESS_FULL, held)
    for index, original in enumerate(placeholders):
        held = held.replace(f"\0ADDR{index}\0", original)
    return held


__all__ = [
    "OPERATOR_ADDRESS_FULL",
    "OPERATOR_ADDRESS_SHORT",
    "apply_operator_address",
    "normalize_speaker_kind",
]
