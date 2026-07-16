"""Bounded sandbox session enablement (env force or in-process button toggle)."""

from __future__ import annotations

import os
from typing import Any

_session_enabled = False


def env_forced() -> bool:
    return os.environ.get("AXON_SAFE_IMPROVEMENT_ENABLED") == "1"


def is_enabled() -> bool:
    return env_forced() or _session_enabled


def session_enabled() -> bool:
    return _session_enabled


def enable_session() -> dict[str, Any]:
    global _session_enabled
    _session_enabled = True
    return status()


def disable_session() -> dict[str, Any]:
    global _session_enabled
    _session_enabled = False
    return status()


def status() -> dict[str, Any]:
    forced = env_forced()
    active = is_enabled()
    if forced:
        source = "env"
    elif _session_enabled:
        source = "session"
    else:
        source = "off"
    return {
        "enabled": active,
        "session_enabled": _session_enabled,
        "env_forced": forced,
        "source": source,
    }


def reset_session_for_tests() -> None:
    """Clear in-process session flag (unit tests only)."""
    global _session_enabled
    _session_enabled = False
