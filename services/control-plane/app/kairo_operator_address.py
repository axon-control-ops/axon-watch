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

    - No guest: bare "sir" becomes "Sir King" for every speaker.
    - Guest active: keep "Sir King" (primary listener); rewrite bare "sir"
      to the guest name (utterance directed at the introduced person).
    - ``speaker_kind`` is retained for call-site compatibility; address form
      no longer differs by speaker when the primary listener is addressed.
    """
    del speaker_kind  # API compatibility; no speaker-specific rewrite path.
    cleaned = str(text or "")
    if not cleaned:
        return cleaned

    name = str(guest_name or "").strip()

    # Hold "Sir King" so bare-sir rewrites cannot corrupt it.
    placeholders: list[str] = []

    def _hold(match: re.Match[str]) -> str:
        placeholders.append(match.group(0))
        return f"\0ADDR{len(placeholders) - 1}\0"

    held = _SIR_KING_RE.sub(_hold, cleaned)
    if name:
        held = _SIR_RE.sub(name, held)
    else:
        held = _SIR_RE.sub(OPERATOR_ADDRESS_FULL, held)
    for index, original in enumerate(placeholders):
        # Normalize held Sir King tokens to the canonical form.
        held = held.replace(f"\0ADDR{index}\0", OPERATOR_ADDRESS_FULL)
    return held


__all__ = [
    "OPERATOR_ADDRESS_FULL",
    "OPERATOR_ADDRESS_SHORT",
    "apply_operator_address",
    "normalize_speaker_kind",
]
