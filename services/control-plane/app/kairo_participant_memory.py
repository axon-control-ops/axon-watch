"""Session-scoped guest participant memory for VAXON address style."""

from __future__ import annotations

import hashlib
import re

_PARTICIPANT_MEMORY: dict[str, str] = {}

_BLOCKED_NAMES = frozenset(
    {
        "me",
        "you",
        "us",
        "him",
        "her",
        "them",
        "sir",
        "madam",
        "vaxon",
        "kairo",
        "axon",
        "operator",
        "user",
        "human",
        "everyone",
        "somebody",
        "someone",
        "anybody",
        "anyone",
        "the",
        "a",
        "an",
        "this",
        "that",
        "here",
        "there",
        "please",
        "now",
    }
)

_INTRO_RE = re.compile(
    r"\b(?:"
    r"this\s+is|"
    r"(?:i(?:'d|\s+would)\s+like\s+you\s+to\s+)?meet|"
    r"say\s+hello\s+to|"
    r"introduce(?:\s+you)?\s+to|"
    r"(?:you(?:'re|\s+are)\s+)?(?:talking|speaking)\s+(?:to|with)|"
    r"address\s+"
    r")\s+"
    r"([A-Za-z][A-Za-z'-]{1,30}(?:\s+[A-Za-z][A-Za-z'-]{1,30})?)"
    r"\b",
    re.IGNORECASE,
)

_CLEAR_RE = re.compile(
    r"\b(?:(?:talk|speak|address)\s+(?:to\s+)?me|just\s+me|back\s+to\s+me)\b",
    re.IGNORECASE,
)


def _session_key(session_id: str) -> str:
    cleaned = str(session_id or "default").strip() or "default"
    return hashlib.sha256(cleaned.encode("utf-8")).hexdigest()[:16]


def _normalize_name(raw: str) -> str | None:
    cleaned = re.sub(r"\s+", " ", str(raw or "").strip(" .,!?;:\"'"))
    if not cleaned:
        return None
    parts = cleaned.split(" ")
    if len(parts) > 2:
        parts = parts[:2]
    if any(part.lower() in _BLOCKED_NAMES for part in parts):
        return None
    if any(not re.fullmatch(r"[A-Za-z][A-Za-z'-]{1,30}", part) for part in parts):
        return None
    return " ".join(part[:1].upper() + part[1:] for part in parts)


def detect_participant_introduction(content: str) -> str | None:
    """Return an introduced guest name, or None when no introduction is found."""
    match = _INTRO_RE.search(str(content or ""))
    if not match:
        return None
    return _normalize_name(match.group(1))


def should_clear_participant(content: str) -> bool:
    return bool(_CLEAR_RE.search(str(content or "")))


def remember_participant(session_id: str, name: str) -> str | None:
    normalized = _normalize_name(name)
    if not normalized:
        return None
    _PARTICIPANT_MEMORY[_session_key(session_id)] = normalized
    return normalized


def clear_participant(session_id: str) -> None:
    _PARTICIPANT_MEMORY.pop(_session_key(session_id), None)


def get_active_participant(session_id: str) -> str | None:
    name = _PARTICIPANT_MEMORY.get(_session_key(session_id))
    return name or None


def update_participant_from_utterance(session_id: str, content: str) -> str | None:
    """Update memory from an operator utterance; return active guest name if any."""
    if should_clear_participant(content):
        clear_participant(session_id)
        return None
    introduced = detect_participant_introduction(content)
    if introduced:
        return remember_participant(session_id, introduced)
    return get_active_participant(session_id)


def apply_participant_address(
    text: str,
    guest_name: str | None,
    *,
    speaker_kind: str = "vaxon",
) -> str:
    """Apply guest-name / Sir / Sir King addressing for the active speaker."""
    from app.kairo_operator_address import apply_operator_address

    return apply_operator_address(
        text,
        _normalize_name(guest_name or "") if guest_name else None,
        speaker_kind=speaker_kind,
    )


def reset_participant_memory_for_tests() -> None:
    _PARTICIPANT_MEMORY.clear()
