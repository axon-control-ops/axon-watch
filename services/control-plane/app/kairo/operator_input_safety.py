"""Classify pasted Mission Control evidence before it reaches an action lane.

The operator bar deliberately accepts both questions and commands.  A pasted
Lead receipt can therefore contain imperative-looking words (``push``,
``Start`` or ``run``) without being an instruction from the operator.  These
helpers make that distinction server-side, where a stale browser bundle or a
different client cannot bypass it.
"""

from __future__ import annotations

import re


_OPERATIONAL_ID_RE = re.compile(
    r"\b(?:run_[a-z0-9]+|task-[a-z0-9]+|lead-plan-[a-z0-9]+)\b",
    re.IGNORECASE,
)
_ROLLUP_LABEL_RE = re.compile(
    r"(?:^|\n)\s*(?:lead\s+rollup|done|verified(?:\s+in\s+flight)?|"
    r"still\s+open(?:\s+on\s+plan)?|next|blocker|outcome|acceptance)\s*:",
    re.IGNORECASE,
)
_ROLLUP_HEADER_RE = re.compile(r"^\s*lead\s+rollup\b", re.IGNORECASE)


def is_pasted_operational_context(content: str) -> bool:
    """Whether text looks like a copied run/Lead receipt instead of a command.

    Require both a receipt signal and enough structured evidence.  This avoids
    treating normal questions such as "what is the next task?" as pasted text.
    """
    trimmed = str(content or "").strip()
    if not trimmed:
        return False
    identifiers = len(_OPERATIONAL_ID_RE.findall(trimmed))
    has_rollup_shape = bool(
        _ROLLUP_HEADER_RE.search(trimmed) or _ROLLUP_LABEL_RE.search(trimmed)
    )
    return bool(
        has_rollup_shape
        and (
            identifiers >= 2
            or (identifiers >= 1 and len(trimmed) >= 280)
            or (len(trimmed) >= 500 and "\n" in trimmed)
        )
    )


__all__ = ["is_pasted_operational_context"]
