"""Private CLI homes used by Axon-X without mutating desktop-app sessions."""

from __future__ import annotations

import os
from pathlib import Path


def _profile_root(env: dict[str, str]) -> Path:
    configured = str(env.get("AXON_WATCH_RUNTIME_PROFILE_ROOT") or "").strip()
    if configured:
        return Path(configured).expanduser()
    state_dir = str(env.get("AXON_WATCH_STATE_DIR") or "").strip()
    if state_dir:
        return Path(state_dir).expanduser() / "runtime-profiles"
    return Path(__file__).resolve().parents[4] / ".local" / "state" / "runtime-profiles"


def codex_profile_env(env: dict[str, str] | None = None) -> dict[str, str]:
    """Return an env whose Codex credentials belong only to Axon-X."""
    shaped = dict(env or os.environ)
    configured = str(shaped.get("AXON_WATCH_CODEX_HOME") or "").strip()
    profile = Path(configured).expanduser() if configured else _profile_root(shaped) / "codex"
    profile.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        profile.chmod(0o700)
    except OSError:
        pass
    shaped["CODEX_HOME"] = str(profile)
    shaped["AXON_WATCH_AUTH_PROFILE"] = "isolated"
    return shaped
