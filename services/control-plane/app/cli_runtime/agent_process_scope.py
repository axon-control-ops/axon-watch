"""Optionally run CLI agent processes in a transient systemd user scope.

Keeps cursor-agent / jest / tsserver memory outside the control-plane unit so
systemd-oomd can kill an overweight agent without taking down the API.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from uuid import uuid4


def agent_scope_enabled() -> bool:
    raw = os.environ.get("AXON_WATCH_AGENT_SYSTEMD_SCOPE", "1").strip().lower()
    return raw not in {"0", "false", "off", "no"}


def agent_scope_memory_max() -> str:
    return os.environ.get("AXON_WATCH_AGENT_MEMORY_MAX", "2G").strip() or "2G"


def agent_scope_memory_high() -> str:
    explicit = os.environ.get("AXON_WATCH_AGENT_MEMORY_HIGH", "").strip()
    if explicit:
        return explicit
    memory_max = agent_scope_memory_max()
    upper = memory_max.upper()
    if upper.endswith("G"):
        try:
            gig = float(upper[:-1])
            # Soft reclaim at ~75% of the hard cap.
            return f"{max(512, int(gig * 768))}M"
        except ValueError:
            pass
    return memory_max


def _systemd_user_available() -> bool:
    if not shutil.which("systemd-run"):
        return False
    try:
        return Path(f"/run/user/{os.getuid()}/systemd/private").exists()
    except OSError:
        return False


def agent_scope_unit_from_wrapped_command(command: list[str] | str | None) -> str | None:
    """Return the transient scope unit name when *command* was wrapped by systemd-run."""
    if not command:
        return None
    parts = command if isinstance(command, list) else str(command).split()
    if not parts or parts[0] != "systemd-run":
        return None
    for part in parts:
        if str(part).startswith("--unit="):
            unit = str(part).split("=", 1)[1].strip()
            return unit or None
    return None


def stop_agent_scope(unit: str) -> bool:
    """Stop a transient agent scope so operator cancel cannot leave cursor-agent running."""
    cleaned = str(unit or "").strip()
    if not cleaned or not _systemd_user_available():
        return False
    systemctl = shutil.which("systemctl")
    if not systemctl:
        return False
    scope_unit = cleaned if cleaned.endswith(".scope") else f"{cleaned}.scope"
    try:
        result = subprocess.run(
            [systemctl, "--user", "stop", scope_unit],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def wrap_command_in_agent_scope(command: list[str]) -> list[str]:
    """Prefix *command* with systemd-run --user --scope when isolation is available."""
    cleaned = [str(part) for part in command if str(part)]
    if not cleaned or not agent_scope_enabled() or not _systemd_user_available():
        return cleaned

    unit = f"axon-agent-{uuid4().hex[:10]}"
    memory_max = agent_scope_memory_max()
    memory_high = agent_scope_memory_high()
    return [
        "systemd-run",
        "--user",
        "--scope",
        "--collect",
        # Without --quiet, systemd-run prints "Running scope as unit: ...;
        # invocation ID: ..." to stderr before the wrapped command even
        # starts. When the CLI itself then fails without any parseable error
        # of its own, callers fall back to this stderr text as "the reason it
        # failed" — surfacing systemd plumbing instead of (or masking) the
        # real cause. Silence it so a genuine empty-stderr failure reads as
        # "exited with status N" rather than an unrelated scope/invocation ID.
        "--quiet",
        f"--unit={unit}",
        f"--property=MemoryMax={memory_max}",
        f"--property=MemoryHigh={memory_high}",
        "--",
        *cleaned,
    ]
