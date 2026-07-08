"""Normalize common STT mishears of the VAXON wake word and key voice entities."""

from __future__ import annotations

import re

from app.operator_persona_name import OPERATOR_PERSONA_NAME

_PERSONA_STT_MISHEAR_REPLACEMENTS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bv[\s.\-_]*a[\s.\-_]*x[\s.\-_]*o[\s.\-_]*n\b", re.IGNORECASE), OPERATOR_PERSONA_NAME),
    (re.compile(r"\bkairos\b", re.IGNORECASE), OPERATOR_PERSONA_NAME),
    (re.compile(r"\bkairo\b", re.IGNORECASE), OPERATOR_PERSONA_NAME),
    (re.compile(r"\bcairo\b", re.IGNORECASE), OPERATOR_PERSONA_NAME),
    (re.compile(r"\bkyro\b", re.IGNORECASE), OPERATOR_PERSONA_NAME),
    (
        re.compile(
            r"\baxon[\s-]+v(?:ax|ix|ex|ick|ik|ack|ox|ux|ics|ic)[a-z]*(?:on|en|in|an|om|un)?\b",
            re.IGNORECASE,
        ),
        OPERATOR_PERSONA_NAME,
    ),
    (re.compile(r"\bvax[\s-]+on\b", re.IGNORECASE), OPERATOR_PERSONA_NAME),
    (re.compile(r"\bwax[\s-]+on\b", re.IGNORECASE), OPERATOR_PERSONA_NAME),
    (re.compile(r"\bvex[\s-]+on\b", re.IGNORECASE), OPERATOR_PERSONA_NAME),
    (re.compile(r"\bfix[\s-]+on\b", re.IGNORECASE), OPERATOR_PERSONA_NAME),
    (re.compile(r"\bbacks?[\s-]+on\b", re.IGNORECASE), OPERATOR_PERSONA_NAME),
    (re.compile(r"\bback[\s-]+son\b", re.IGNORECASE), OPERATOR_PERSONA_NAME),
    (re.compile(r"\bvack[\s-]+s?[\s-]*on\b", re.IGNORECASE), OPERATOR_PERSONA_NAME),
    (re.compile(r"\bvic(?:k|s)?[\s-]+s?[\s-]*on\b", re.IGNORECASE), OPERATOR_PERSONA_NAME),
    (re.compile(r"\bvi(?:ck|x|k)?[\s-]+s?[\s-]*on\b", re.IGNORECASE), OPERATOR_PERSONA_NAME),
    (re.compile(r"\bvicksen\b", re.IGNORECASE), OPERATOR_PERSONA_NAME),
    (re.compile(r"\bvicksin\b", re.IGNORECASE), OPERATOR_PERSONA_NAME),
    (re.compile(r"\bvickson\b", re.IGNORECASE), OPERATOR_PERSONA_NAME),
    (re.compile(r"\bvikson\b", re.IGNORECASE), OPERATOR_PERSONA_NAME),
    (re.compile(r"\bviksen\b", re.IGNORECASE), OPERATOR_PERSONA_NAME),
    (re.compile(r"\bviksin\b", re.IGNORECASE), OPERATOR_PERSONA_NAME),
    (re.compile(r"\bvicson\b", re.IGNORECASE), OPERATOR_PERSONA_NAME),
    (re.compile(r"\bvicsen\b", re.IGNORECASE), OPERATOR_PERSONA_NAME),
    (re.compile(r"\bvicen\b", re.IGNORECASE), OPERATOR_PERSONA_NAME),
    (re.compile(r"\bvixson\b", re.IGNORECASE), OPERATOR_PERSONA_NAME),
    (re.compile(r"\bvixen\b", re.IGNORECASE), OPERATOR_PERSONA_NAME),
    (re.compile(r"\bwixen\b", re.IGNORECASE), OPERATOR_PERSONA_NAME),
    (re.compile(r"\bwicksen\b", re.IGNORECASE), OPERATOR_PERSONA_NAME),
    (re.compile(r"\bvic+[kt]?sen\b", re.IGNORECASE), OPERATOR_PERSONA_NAME),
    (re.compile(r"\bvi[ckx]{1,2}s?[oei]n\b", re.IGNORECASE), OPERATOR_PERSONA_NAME),
    (re.compile(r"\bvaxen\b", re.IGNORECASE), OPERATOR_PERSONA_NAME),
    (re.compile(r"\bvexon\b", re.IGNORECASE), OPERATOR_PERSONA_NAME),
    (re.compile(r"\bwexon\b", re.IGNORECASE), OPERATOR_PERSONA_NAME),
    (re.compile(r"\bwaxon\b", re.IGNORECASE), OPERATOR_PERSONA_NAME),
    (re.compile(r"\bnaxon\b", re.IGNORECASE), OPERATOR_PERSONA_NAME),
    (re.compile(r"\bvixon\b", re.IGNORECASE), OPERATOR_PERSONA_NAME),
    (re.compile(r"\bvyxon\b", re.IGNORECASE), OPERATOR_PERSONA_NAME),
    (re.compile(r"\bvaccine\b", re.IGNORECASE), OPERATOR_PERSONA_NAME),
    (re.compile(r"\bexcent\b", re.IGNORECASE), OPERATOR_PERSONA_NAME),
    (re.compile(r"\baccent\b", re.IGNORECASE), OPERATOR_PERSONA_NAME),
)

_PERSONA_STT_PHONETIC_VAXON_RE = re.compile(
    r"\b[vwbfmpn][aeiouy]?[ -]?(?:ax|ex|ix|ick|iks|ik|ack|acs|ox|ux|ics|ic|ec)"
    r"(?:[a-z]{0,2})?(?:on|en|in|an|om|un)\b",
    re.IGNORECASE,
)

_COMMON_STT_ENTITY_REPLACEMENTS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bdash[\s-]*pro\b", re.IGNORECASE), "DashPro"),
    (re.compile(r"\bprobox[\s-]*space\b", re.IGNORECASE), "DashPro workspace"),
    (re.compile(r"\bworks?\s*based\b", re.IGNORECASE), "workspace"),
    (
        re.compile(
            r"\b(?:best|this|test|desk|those|these)\s+pro\s+workspace\s+justick\b",
            re.IGNORECASE,
        ),
        "DashPro workspace just did",
    ),
    (
        re.compile(
            r"\bthis\s+pro\s+workspace\s+use\s+it\b",
            re.IGNORECASE,
        ),
        "DashPro workspace just did",
    ),
    (
        re.compile(
            r"\b(?:best|this|test|desk|those|these)\s+pro\s+workspace\b",
            re.IGNORECASE,
        ),
        "DashPro workspace",
    ),
    (
        re.compile(
            r"\bthis\s+pro\s+workspace\b",
            re.IGNORECASE,
        ),
        "DashPro workspace",
    ),
    (re.compile(r"\bjustick\b", re.IGNORECASE), "just did"),
)


def normalize_persona_stt_aliases(text: str) -> str:
    result = text
    for pattern, replacement in _PERSONA_STT_MISHEAR_REPLACEMENTS:
        result = pattern.sub(replacement, result)
    result = _PERSONA_STT_PHONETIC_VAXON_RE.sub(OPERATOR_PERSONA_NAME, result)
    for pattern, replacement in _COMMON_STT_ENTITY_REPLACEMENTS:
        result = pattern.sub(replacement, result)
    return result
