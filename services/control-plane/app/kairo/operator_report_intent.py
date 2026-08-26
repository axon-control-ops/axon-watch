"""Intent matching for explicit VAXON fleet-report requests."""

from __future__ import annotations

import re

_HOTWORD_RE = re.compile(
    r"^(?:report|status(?:\s+report)?|update|stand[\s-]?up|"
    r"where\s+do\s+we\s+stand|where\s+are\s+we(?:\s+now)?|"
    r"what(?:'?s| is)\s+(?:going\s+on|happening))\s*[.!]?\s*$",
    re.IGNORECASE,
)
_PHRASE_RE = re.compile(
    r"\b(status report|stand[\s-]?up|where things stand|where do we stand|"
    r"roll.?up|brief(?:ing)? me|jarvis-style second-brain stand-up|"
    r"what each teammate|team status|single best next move|work in flight|"
    r"lead rollups?|fleet report|detailed report|full report|"
    r"give me (?:a |the )?report|show me (?:a |the )?report|"
    r"summari[sz]e (?:all |the )?(?:work|workspaces|workspace work|team work))\b",
    re.IGNORECASE,
)
_WORD_ASK_RE = re.compile(
    r"(?:^|[—\-,:;]\s*)report(?:\s*[—\-:]|\s+on\b|\s*$)", re.IGNORECASE
)


def is_operator_report_request(content: str) -> bool:
    """Return true for a stand-up ask, but not a completion 'report back'."""
    trimmed = str(content or "").strip()
    if not trimmed:
        return False
    if _HOTWORD_RE.match(trimmed):
        return True
    lower = trimmed.lower()
    if re.search(r"\breport\s+back\b", lower):
        return False
    if lower.startswith(("report —", "report -")):
        return True
    return bool(_PHRASE_RE.search(trimmed) or _WORD_ASK_RE.search(trimmed))
