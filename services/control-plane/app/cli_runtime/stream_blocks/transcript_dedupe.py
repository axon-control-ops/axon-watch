"""Transcript deduplication helpers for research stream blocks."""

from __future__ import annotations

import re
from difflib import SequenceMatcher

_SUFFIX_ECHO_MIN = 80
_SUFFIX_ECHO_SEMANTIC_MIN = 60
# Sentence end immediately followed by a capital / quote (often glued: "loop.No —").
_GLUED_SENTENCE_RESTART_RE = re.compile(
    r'(?<=[.!?…])(["\'"\u2018\u2019\u201c\u201d\)\]]*)(?=[A-Z"\u201c\u2018])'
)
_MARKDOWN_HEADING_RE = re.compile(r"(?m)^\*\*[^*\n]+?\*\*\s*$")


def _semantic_prose_key(text: str) -> str:
    return re.sub(r"\W+", "", text or "").lower()


def _suffix_is_echo_of_prefix(left: str, right: str) -> bool:
    """True when *right* largely restates content already present in *left*."""
    if len(right) < _SUFFIX_ECHO_MIN or len(left) < _SUFFIX_ECHO_MIN:
        return False
    sk_left = _semantic_prose_key(left)
    sk_right = _semantic_prose_key(right)
    if len(sk_right) < _SUFFIX_ECHO_SEMANTIC_MIN or len(sk_left) < _SUFFIX_ECHO_SEMANTIC_MIN:
        return False
    if sk_right in sk_left:
        return True

    # Aggregates sometimes skip a middle section, so the echo is not a contiguous
    # substring even when every token already appeared earlier.
    if len(right) > len(left) + 64:
        return False

    right_tokens = set(re.findall(r"[a-z0-9]+", right.lower()))
    left_tokens = set(re.findall(r"[a-z0-9]+", left.lower()))
    if not right_tokens:
        return False
    overlap = len(right_tokens & left_tokens) / len(right_tokens)
    if overlap < 0.92:
        return False

    # Require the echo to restart text that already appeared (not a new section
    # that merely shares common words).
    restart_key = _semantic_prose_key(right[:160])
    if len(restart_key) < 40 or restart_key not in sk_left:
        # Fall back: long shared contiguous stem.
        stem = sk_right[: max(_SUFFIX_ECHO_SEMANTIC_MIN, len(sk_right) * 3 // 4)]
        if not stem or stem not in sk_left:
            matcher = SequenceMatcher(None, sk_left, sk_right)
            if matcher.quick_ratio() < 0.9 or matcher.ratio() < 0.86:
                return False
    return True


def _collapse_contained_suffix_echo(text: str) -> str | None:
    """Drop a trailing partial replay glued or blank-line-separated onto earlier prose.

    Cursor can emit a final aggregate that restarts mid-reply (often after a list),
    e.g. ``...daily loop.No — that…`` + a second copy of a markdown section.

    Keep this cheap: history loads re-normalize every agent message, so scanning
    every blank line / sentence boundary on 100KB transcripts is too expensive.
    """
    if len(text) < _SUFFIX_ECHO_MIN * 2:
        return None

    # Echoes append near the end — ignore the leading half.
    min_split = max(_SUFFIX_ECHO_MIN, len(text) // 2)
    candidates: list[int] = []

    glued = [
        match.end()
        for match in _GLUED_SENTENCE_RESTART_RE.finditer(text)
        if match.end() >= min_split
    ]
    # Only the trailing glued restarts matter (Cursor glues the aggregate at the end).
    candidates.extend(glued[-12:])

    seen_heading: dict[str, int] = {}
    for match in _MARKDOWN_HEADING_RE.finditer(text):
        key = _semantic_prose_key(match.group(0))
        if not key:
            continue
        if key not in seen_heading:
            seen_heading[key] = match.start()
            continue
        if match.start() >= min_split:
            candidates.append(match.start())

    if not candidates:
        return None

    for split in sorted(set(candidates)):
        left = text[:split].rstrip()
        right = text[split:].lstrip()
        if _suffix_is_echo_of_prefix(left, right):
            return left
    return None


def collapse_duplicated_body(content: str) -> str:
    """Collapse assistant prose that was echoed back-to-back in full.

    Cursor stream-json can emit a final aggregate assistant event that repeats
    the entire markdown reply (common for bullet lists with single newlines).
    It can also glue a *partial* replay onto the end of an earlier section.
    """
    if not content:
        return content

    stripped = content.strip()
    if not stripped:
        return content

    text = stripped.replace("\r\n", "\n")

    if len(text) >= 2 and len(text) % 2 == 0:
        half = len(text) // 2
        if text[:half] == text[half:]:
            return text[:half]

    if len(text) >= 2:
        mid = len(text) // 2
        left = text[:mid].strip()
        right = text[mid:].strip()
        if left and left == right:
            return left

    lines = text.split("\n")
    if len(lines) >= 2 and len(lines) % 2 == 0:
        half = len(lines) // 2
        if lines[:half] == lines[half:]:
            return "\n".join(lines[:half])

    paragraphs = [chunk.strip() for chunk in re.split(r"\n{2,}", text) if chunk.strip()]
    if len(paragraphs) >= 2 and len(paragraphs) % 2 == 0:
        half = len(paragraphs) // 2
        if paragraphs[:half] == paragraphs[half:]:
            return "\n\n".join(paragraphs[:half])

    # Two copies separated by a blank line.
    if "\n\n" in text:
        left, right = text.split("\n\n", 1)
        if left.strip() and left.strip() == right.strip():
            return left.strip()

    contained = _collapse_contained_suffix_echo(text)
    if contained is not None:
        return contained

    return content


def _dedupe_plain_paragraphs(content: str) -> str:
    paragraphs = [chunk.strip() for chunk in re.split(r"\n{2,}", content.strip()) if chunk.strip()]
    deduped: list[str] = []
    for paragraph in paragraphs:
        if deduped and deduped[-1] == paragraph:
            continue
        deduped.append(paragraph)
    return "\n\n".join(deduped)


def _paragraphs_from_prose(text: str) -> list[str]:
    return [chunk.strip() for chunk in re.split(r"\n{2,}", text.strip()) if chunk.strip()]


def _filter_seen_paragraphs(text: str, seen: set[str]) -> str:
    """Drop prose paragraphs that already appeared earlier in the transcript."""
    if not text.strip():
        return text

    kept: list[str] = []
    for paragraph in _paragraphs_from_prose(text):
        if paragraph in seen:
            continue
        seen.add(paragraph)
        kept.append(paragraph)
    return "\n\n".join(kept)


_EDIT_HEADER_RE = re.compile(r"^:::edit\s+.+?\s+\+\d+\s+-\d+\s*$")
_TOOL_HEADER_RE = re.compile(r"^:::tool\s+.+$")
_RESEARCH_HEADER_RE = re.compile(r"^:::research\s+.+$")
_TERMINAL_HEADER_RE = re.compile(r"^:::terminal\s+.+$")
_BLOCK_START_RE = re.compile(r"^:::(thinking|edit|terminal|tool|research)\b", re.MULTILINE)


def _is_transcript_block_start(line: str) -> bool:
    stripped = line.strip()
    if stripped == ":::thinking":
        return True
    return bool(
        _EDIT_HEADER_RE.match(stripped)
        or _TOOL_HEADER_RE.match(stripped)
        or _RESEARCH_HEADER_RE.match(stripped)
        or _TERMINAL_HEADER_RE.match(stripped)
    )


def _advance_past_transcript_block(lines: list[str], start: int) -> int:
    line = lines[start]
    stripped = line.strip()
    if _TOOL_HEADER_RE.match(stripped):
        return start + 1

    index = start + 1
    while index < len(lines):
        if lines[index].strip() == ":::":
            return index + 1
        index += 1
    return len(lines)


def _dedupe_prose_segment(content: str) -> str:
    """Collapse duplicate lines/paragraphs inside a prose-only transcript gap."""
    if not content.strip():
        return content

    leading = len(content) - len(content.lstrip("\n"))
    trailing = len(content) - len(content.rstrip("\n"))
    body = content.strip("\n")
    if not body:
        return content

    deduped_lines: list[str] = []
    for line in body.split("\n"):
        if line.strip() and deduped_lines and deduped_lines[-1].strip() == line.strip():
            continue
        if not line.strip() and deduped_lines and not deduped_lines[-1].strip():
            continue
        deduped_lines.append(line)

    body = _dedupe_plain_paragraphs("\n".join(deduped_lines))
    return ("\n" * leading) + body + ("\n" * trailing)


def _dedupe_block_structured_paragraphs(content: str) -> str:
    lines = content.split("\n")
    chunks: list[str] = []
    prose_buf: list[str] = []
    seen_paragraphs: set[str] = set()
    index = 0

    def flush_prose() -> None:
        nonlocal prose_buf
        if not prose_buf:
            return
        local = _dedupe_prose_segment("\n".join(prose_buf))
        filtered = _filter_seen_paragraphs(local, seen_paragraphs)
        if filtered.strip():
            chunks.append(filtered)
        prose_buf = []

    while index < len(lines):
        line = lines[index]
        if _is_transcript_block_start(line):
            flush_prose()
            end = _advance_past_transcript_block(lines, index)
            chunks.append("\n".join(lines[index:end]))
            index = end
            continue
        prose_buf.append(line)
        index += 1

    flush_prose()
    return "\n".join(chunks)


def dedupe_assistant_paragraphs(content: str) -> str:
    """Collapse exact duplicate paragraphs in plain assistant prose only."""
    if not content.strip():
        return content
    if _BLOCK_START_RE.search(content):
        return _dedupe_block_structured_paragraphs(content)

    marker_index = content.rfind("\n:::\n")
    if marker_index >= 0:
        prefix = content[: marker_index + len("\n:::\n")]
        suffix = content[marker_index + len("\n:::\n") :]
        deduped_suffix = _dedupe_plain_paragraphs(suffix)
        return f"{prefix}{deduped_suffix}" if deduped_suffix else prefix.rstrip()

    return _dedupe_plain_paragraphs(content)