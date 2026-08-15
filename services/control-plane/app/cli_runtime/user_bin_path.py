"""User-local binary PATH helpers for headless agent runtimes."""

from __future__ import annotations

import os
from pathlib import Path

SYSTEM_BIN_PATHS = (
    "/usr/local/sbin",
    "/usr/local/bin",
    "/usr/sbin",
    "/usr/bin",
    "/sbin",
    "/bin",
)


def existing_user_local_bin(home: Path | None = None) -> Path | None:
    root = home or Path("/home/vaxon")
    candidate = root / ".local" / "bin"
    return candidate if candidate.is_dir() else None


def runtime_path_with_user_bins(current_path: str, *, home: Path | None = None) -> str:
    parts = [part for part in str(current_path or "").split(os.pathsep) if part]
    for path in (existing_user_local_bin(home), *(Path(item) for item in SYSTEM_BIN_PATHS)):
        if path is not None and str(path) not in parts and path.exists():
            parts.append(str(path))
    return os.pathsep.join(parts)


def sandbox_path_with_user_bins(user_local_bin: Path | None = None) -> str:
    parts = ["/run/axon-agent-policy/bin"]
    if user_local_bin is not None:
        parts.append(str(user_local_bin))
    parts.extend(SYSTEM_BIN_PATHS)
    return ":".join(parts)
