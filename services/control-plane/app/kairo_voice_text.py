"""Pure text normalization helpers for KAIRO spoken lines."""

from __future__ import annotations

import re

from app.operator_persona_name import OPERATOR_PERSONA_NAME, OPERATOR_PERSONA_SPOKEN_NAME
from app.kairo_spoken_symbol_words import strip_literal_symbol_words

_STREAM_BLOCK_START_RE = re.compile(
    r"^:::(?:thinking|tool|edit|terminal|research)\b",
    re.IGNORECASE,
)
_STREAM_BLOCK_CLOSE_RE = re.compile(r"^:::\s*$")
_PATH_ONLY_RE = re.compile(r"^[\w./_-]+$")
_MAX_SPOKEN_CHARS = 1400
_MAX_DISPLAY_CHARS = 1600

_ANSWER_CUE_RE = re.compile(
    r"\b(from my side|right|here's|nothing urgent|systems nominal|not spiking|you have|I'd|all quiet)\b",
    re.IGNORECASE,
)


def _strip_stream_blocks(text: str) -> str:
    """Drop ``:::thinking``/``:::tool`` stream sections emitted by the CLI."""
    kept: list[str] = []
    skipping = False
    for line in str(text or "").splitlines():
        stripped = line.strip()
        if _STREAM_BLOCK_START_RE.match(stripped):
            skipping = True
            continue
        if skipping:
            if _STREAM_BLOCK_CLOSE_RE.match(stripped) or not stripped:
                skipping = False
            continue
        if stripped.startswith(":::"):
            continue
        kept.append(line)
    return "\n".join(kept).strip()


def _dedupe_doubled_text(text: str) -> str:
    """Streamed output sometimes repeats the final sentence back-to-back."""
    half = len(text) // 2
    if half and text[:half].strip() == text[half:].strip():
        return text[:half].strip()
    return text


def _dedupe_repeated_sentences(text: str) -> str:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    deduped: list[str] = []
    seen: set[str] = set()
    for part in parts:
        cleaned = part.strip()
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(cleaned)
    return " ".join(deduped).strip()


def _strip_markdown_for_speech(text: str) -> str:
    text = re.sub(r"```[\s\S]*?```", " ", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = text.replace('"', " ").replace("'", "'")
    return text


def _prepare_persona_name_for_speech(text: str) -> str:
    """Speak as Vekson (vek-son) — never letter-spell V-A-X-O-N."""
    text = re.sub(
        r"\bV\s*[.\-]\s*A\s*[.\-]\s*X\s*[.\-]\s*O\s*[.\-]\s*N\b",
        OPERATOR_PERSONA_SPOKEN_NAME,
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\bV\s+A\s+X\s+O\s+N\b",
        OPERATOR_PERSONA_SPOKEN_NAME,
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\bVAXON\b", OPERATOR_PERSONA_SPOKEN_NAME, text, flags=re.IGNORECASE)
    # Sesotho name — keep display text as Thabo, guide TTS to TA-bo.
    text = re.sub(r"\bThabo\b", "Ta-bo", text, flags=re.IGNORECASE)
    # Zulu name — speak Sipho as SEE-po (not SIFO).
    return re.sub(r"\bSipho\b", "See-po", text, flags=re.IGNORECASE)


def _soften_symbols_for_speech(text: str) -> str:
    """Keep TTS from reading punctuation/symbol names aloud."""
    # Emoji / pictographs (incl. many "smiley" ranges).
    text = re.sub(
        r"[\U0001F300-\U0001FAFF\U00002700-\U000027BF\U00002600-\U000026FF]",
        " ",
        text,
    )
    # Paths / URLs: turn separators into spaces instead of spoken "slash".
    text = text.replace("\\", " ").replace("/", " ")
    text = text.replace("_", " ").replace("|", " ")
    text = text.replace("#", " ").replace("@", " ").replace("*", " ")
    text = text.replace("→", " ").replace("←", " ").replace("=>", " ")
    # Preserve clock times (12:30); turn every other colon into a pause.
    _clock_mark = "\ue000"
    text = re.sub(r"\b(\d{1,2}):(\d{2})\b", rf"\1{_clock_mark}\2", text)
    text = text.replace(":", ", ")
    text = text.replace(_clock_mark, ":")
    text = re.sub(r"[<>{}[\]()`~^]", " ", text)
    text = re.sub(r"\s+,", ",", text)
    text = re.sub(r",\s*,+", ",", text)
    return re.sub(r"\s+", " ", text).strip()


def _truncate_at_sentence(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    trimmed = text[:max_chars]
    cut = trimmed.rfind(". ")
    if cut >= max_chars // 2:
        return trimmed[: cut + 1].strip()
    return f"{trimmed.rsplit(' ', 1)[0].strip()}…"


def _readable_paragraphs(text: str) -> list[str]:
    chunks = [chunk.strip() for chunk in re.split(r"\n\s*\n+", text) if chunk.strip()]
    paragraphs: list[str] = []
    for chunk in chunks:
        if chunk.startswith(":::"):
            continue
        if _PATH_ONLY_RE.fullmatch(chunk):
            continue
        if len(chunk) < 16 and "/" in chunk and " " not in chunk:
            continue
        normalized = re.sub(r"\s+", " ", chunk).strip()
        if not normalized:
            continue
        if paragraphs and paragraphs[-1].lower() == normalized.lower():
            continue
        paragraphs.append(normalized)
    return paragraphs


def _extract_readable_reply(text: str, *, max_chars: int = _MAX_SPOKEN_CHARS) -> str:
    paragraphs = _readable_paragraphs(text)
    body = "\n\n".join(paragraphs) if paragraphs else text.strip()
    body = _dedupe_doubled_text(body)
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    if len(body) <= max_chars:
        return body
    return _truncate_at_sentence(body.replace("\n", " "), max_chars)


def _extract_voice_answer(text: str, *, max_chars: int = _MAX_SPOKEN_CHARS) -> str:
    return _extract_readable_reply(text, max_chars=max_chars)


def _strip_forbidden_listener_address(text: str) -> str:
    """Never address the listener as operator/user/human (JARVIS-style)."""
    cleaned = str(text or "")
    # Vocative / greeting forms: "Hello operator", "Right, operator — …"
    cleaned = re.sub(
        r"\b(?:hello|hi|hey)\s+(?:operator|user|human)\b[,!]?\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r",\s*\b(?:operator|user|human)\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(
        r"\b(?:operator|user|human)\s*[—-]\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    # Clinical product phrases that should never be spoken aloud.
    cleaned = re.sub(r"\bfor operator review\b", "for your review", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(
        r"\bnext operator (command|action)\b",
        r"next \1",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\boperator decisions\b", "decisions", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(
        r"\b(?:live|current) operator state\b",
        "current system state",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    cleaned = re.sub(r"\s+([,.!?])", r"\1", cleaned)
    return cleaned.strip()


def _prepare_counts_for_speech(text: str) -> str:
    """Stop TTS from gluing '4 Lead' / 'four Lead' into 'forlead'."""
    number_words = {
        "0": "zero",
        "1": "one",
        "2": "two",
        "3": "three",
        "4": "four",
        "5": "five",
        "6": "six",
        "7": "seven",
        "8": "eight",
        "9": "nine",
        "10": "ten",
        "11": "eleven",
        "12": "twelve",
    }
    count_words = "|".join(number_words.values())

    def _lead_replace(match: re.Match[str]) -> str:
        raw = match.group(1)
        spoken = number_words.get(raw.lower(), number_words.get(raw, raw))
        # Comma + hyphenated Lead-team forces Azure to pause (avoids "forlead").
        return f"{spoken}, Lead-team"

    text = re.sub(
        rf"\b({count_words}|\d{{1,2}})\s+Lead(?:[- ]team)?\b",
        _lead_replace,
        text,
        flags=re.IGNORECASE,
    )

    def _replace(match: re.Match[str]) -> str:
        digits = match.group(1)
        word = match.group(2)
        spoken = number_words.get(digits, digits)
        return f"{spoken} {word}"

    return re.sub(r"\b(\d{1,2})\s+([A-Z][A-Za-z-]+)\b", _replace, text)


def normalize_spoken_line(raw: str, *, max_chars: int = _MAX_SPOKEN_CHARS) -> str:
    """Convert agent/model text into concise operator-facing speech."""
    original = str(raw or "").strip()
    if not original:
        return ""
    text = _strip_stream_blocks(original)
    text = _strip_markdown_for_speech(text)
    text = re.sub(r"([.!?])([A-Z])", r"\1 \2", text)
    if ":::" in original or len(text) > max_chars:
        text = _extract_readable_reply(text, max_chars=max_chars)
    text = _dedupe_doubled_text(text)
    text = _dedupe_repeated_sentences(text)
    text = re.sub(r"^[\"'`]+|[\"'`]+$", "", text)
    text = re.sub(
        rf"^({OPERATOR_PERSONA_NAME}|KAIRO|Jarvis)\s*[:—-]\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = _strip_forbidden_listener_address(text)
    text = _prepare_persona_name_for_speech(text)
    text = _prepare_counts_for_speech(text)
    text = _soften_symbols_for_speech(text)
    text = strip_literal_symbol_words(text)
    text = re.sub(r"\s+", " ", text).strip()
    if text and not text.endswith((".", "!", "?")):
        text = f"{text}."
    return text


__all__ = [
    "normalize_spoken_line",
]
