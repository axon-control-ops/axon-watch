"""Self-healing release ladder. Default stays conservative."""

from __future__ import annotations

import os

from app.platform_recovery.states import AUTONOMY_LEVELS


def configured_autonomy_level() -> int:
    raw = os.environ.get("AXON_WATCH_SELF_HEAL_LEVEL", "1").strip()
    try:
        level = int(raw)
    except ValueError:
        return 1
    if level < 0:
        return 0
    if level > 5:
        return 5
    return level


def autonomy_label(level: int | None = None) -> str:
    resolved = configured_autonomy_level() if level is None else int(level)
    return AUTONOMY_LEVELS.get(resolved, AUTONOMY_LEVELS[1])


def may_auto_reconcile(level: int | None = None) -> bool:
    resolved = configured_autonomy_level() if level is None else int(level)
    return resolved >= 1


def may_auto_retry_low_risk(level: int | None = None) -> bool:
    resolved = configured_autonomy_level() if level is None else int(level)
    return resolved >= 2


def may_auto_resume_checkpoint(level: int | None = None) -> bool:
    resolved = configured_autonomy_level() if level is None else int(level)
    return resolved >= 3
