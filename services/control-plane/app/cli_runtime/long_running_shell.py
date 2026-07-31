"""Classify long-running ship shells (OTA / EAS / Expo) for Axon terminal jobs."""

from __future__ import annotations

import re

# Align with command_executor OTA guards and Expo/EAS ship verbs.
# Intentionally narrow: do not match generic `npm run export` package scripts.
_LONG_RUNNING_SHIP_SHELL_RE = re.compile(
    r"(?:"
    r"\bnpm\s+run\s+ota(?::[\w-]+)?\b"
    r"|\bota:(?:canary|production)\b"
    r"|\beas\s+update\b"
    r"|\bexpo\s+(?:export|publish|update)\b"
    r"|\bnpx\s+expo\s+(?:export|publish|update)\b"
    r")",
    re.IGNORECASE,
)


def is_long_running_ship_shell(command: str) -> bool:
    """Return True when command is an OTA / EAS / Expo export-style ship job."""
    trimmed = str(command or "").strip()
    if not trimmed:
        return False
    return bool(_LONG_RUNNING_SHIP_SHELL_RE.search(trimmed))


__all__ = ["is_long_running_ship_shell"]
