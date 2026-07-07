"""Discover cloudflared binary candidates for tunnel control."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


def _is_executable(path: str) -> bool:
    return bool(path) and os.path.isfile(path) and os.access(path, os.X_OK)


def _expand_candidate(raw: str) -> str:
    return os.path.expandvars(str(raw or "").strip())


def find_cloudflared_binary(candidates: list[str] | tuple[str, ...] | None = None) -> str:
    expanded = [_expand_candidate(item) for item in (candidates or ("cloudflared",))]
    for candidate in expanded:
        if candidate == "cloudflared":
            resolved = shutil.which("cloudflared") or ""
            if _is_executable(resolved):
                return resolved
            continue
        if _is_executable(candidate):
            return candidate
    return ""


def cloudflared_version(binary_path: str) -> str:
    if not _is_executable(binary_path):
        return ""
    try:
        result = subprocess.run(
            [binary_path, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            env={**os.environ, "NO_COLOR": "1"},
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    output = (result.stdout or result.stderr or "").strip()
    return output.splitlines()[0] if output else ""
