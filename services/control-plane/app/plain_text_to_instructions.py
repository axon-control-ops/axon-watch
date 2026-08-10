"""Parse Instructions markdown and detect binding out-of-scope git gates."""

from __future__ import annotations

import re

_INSTRUCTIONS_HEADING_RE = re.compile(r"^#\s*Instructions\b", re.IGNORECASE | re.MULTILINE)
_SECTION_RE = re.compile(
    r"^##\s*(Goal|In scope|Out of scope|Steps|Constraints)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_GIT_OUT_OF_SCOPE_RE = re.compile(
    r"\b(?:commit(?:ting|s)?|push(?:ing|es)?|merg(?:e|ing)|releas(?:e|ing))\b",
    re.IGNORECASE,
)
_NEGATED_COMMIT_RE = re.compile(
    r"\b(?:never|don'?t|do\s+not|did\s+not|no|not|without|wrong)\b"
    r"(?:\s+\w+){0,8}\s+(?:\w+\s+){0,4}?"
    r"(?:commit(?:ting|s)?|push(?:ing|es)?|merg(?:e|ing)|releas(?:e|ing))\b",
    re.IGNORECASE,
)
_AFFIRMATIVE_COMMIT_RE = re.compile(
    r"(?:"
    r"^\s*(?:ok(?:ay)?[,\s]+)?(?:please\s+)?commit\b"
    r"(?:\s+(?:first|these|my|the|all|current|pending|this|those))?"
    r"(?:\s+changes?)?(?:\s+and\s+push)?"
    r"|(?:^|[\s,.:;!\-—])(?:please\s+)?commit\s+"
    r"(?:first|these|my|the|all|current|pending|this|those|changes?\b)"
    r"(?:\s+changes?)?(?:\s+and\s+push)?"
    r"|(?:^|[\s,.:;!\-—])(?:please\s+)?commit\s+and\s+(?![0-9a-f]{7,40}\b)\w+\b"
    r"|(?:^|[\s,.:;!\-—])(?:create\s+(?:a\s+)?commit|git\s+commit)\b"
    r")",
    re.IGNORECASE,
)


def _parse_sections(prompt: str) -> dict[str, str]:
    hits = list(_SECTION_RE.finditer(prompt))
    sections: dict[str, str] = {}
    for index, found in enumerate(hits):
        key = found.group(1).lower().replace(" ", "_")
        body_start = found.end()
        body_end = hits[index + 1].start() if index + 1 < len(hits) else len(prompt)
        sections[key] = prompt[body_start:body_end].strip()
    return sections


def instructions_markdown_present(prompt: str) -> bool:
    return bool(_INSTRUCTIONS_HEADING_RE.search(prompt.strip()))


def instructions_block_git_actions(prompt: str) -> bool:
    """True when Instructions markdown puts git actions out of scope."""
    if not instructions_markdown_present(prompt):
        return False
    out_of_scope = _parse_sections(prompt).get("out_of_scope", "")
    if not out_of_scope:
        return False
    return bool(_GIT_OUT_OF_SCOPE_RE.search(out_of_scope))


def prompt_requests_git_actions(prompt: str) -> bool:
    """True only for affirmative commit/push intent, not negated mentions."""
    stripped = prompt.strip()
    if not stripped:
        return False
    if instructions_block_git_actions(stripped):
        return False
    if _NEGATED_COMMIT_RE.search(stripped):
        return False
    return bool(_AFFIRMATIVE_COMMIT_RE.search(stripped))
