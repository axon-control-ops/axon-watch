"""Secret redaction for persisted autonomous-attention receipts."""

from __future__ import annotations

import re
from typing import Any


_SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)\b([A-Z0-9_]*(?:TOKEN|SECRET|PASSWORD|API_KEY|APIKEY))"
    r"\s*([:=])\s*([^\s,;]+)"
)
_BEARER_RE = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]+")
# Providers sometimes echo a *partially masked* rejected key (for example
# ``sk-admin********suffix``). Treat that as secret material too: even a masked
# prefix/suffix is credential metadata and has no place in persisted chat.
_KNOWN_TOKEN_RE = re.compile(
    r"\b(?:gh[pousr]_[A-Za-z0-9*._-]{8,}|sk-[A-Za-z0-9*._-]{8,})\b"
)
_SENSITIVE_KEY_RE = re.compile(
    r"(?i)(token|secret|password|api[_-]?key|authorization|credential)"
)


def redact_text(value: Any) -> str:
    text = str(value or "")
    text = _SECRET_ASSIGNMENT_RE.sub(r"\1\2[REDACTED]", text)
    text = _BEARER_RE.sub("Bearer [REDACTED]", text)
    return _KNOWN_TOKEN_RE.sub("[REDACTED]", text)


def redact_payload(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): (
                "[REDACTED]"
                if _SENSITIVE_KEY_RE.search(str(key))
                else redact_payload(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_payload(item) for item in value]
    if isinstance(value, tuple):
        return [redact_payload(item) for item in value]
    if isinstance(value, str):
        return redact_text(value)
    return value
