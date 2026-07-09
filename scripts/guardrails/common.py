#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]

DEFAULT_LIMITS = {
    ".py": {"soft": 350, "hard": 500},
    ".js": {"soft": 350, "hard": 500},
    ".ts": {"soft": 350, "hard": 500},
    ".vue": {"soft": 350, "hard": 500},
    ".css": {"soft": 350, "hard": 500},
    ".html": {"soft": 250, "hard": 400},
    ".md": {"soft": 400, "hard": 700},
}

EXCLUDED_PARTS = {
    ".git",
    ".venv",
    "node_modules",
    "__pycache__",
    "dist",
    "build",
    ".turbo",
}

BANNED_FILENAMES = {
    "misc.py",
    "more_helpers.py",
    "big_utils.py",
    "new_logic.js",
}

MANIFEST_PATH = ROOT / "scripts/guardrails/hotspot_budgets.json"


def load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except json.JSONDecodeError as exc:
        rel = path.relative_to(ROOT) if path.is_absolute() else path
        raise ValueError(f"{rel}: invalid JSON ({exc.msg})") from exc


def line_count(path: Path) -> int:
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        return sum(1 for _ in handle)


def should_skip(rel_path: str) -> bool:
    return bool(set(Path(rel_path).parts) & EXCLUDED_PARTS)


def tracked_source_files(root: Path = ROOT) -> list[Path]:
    output = subprocess.check_output(
        ["git", "ls-files"],
        cwd=root,
        text=True,
    )
    files: list[Path] = []
    for rel in output.splitlines():
        if not rel or should_skip(rel):
            continue
        path = root / rel
        if not path.is_file():
            continue
        if path.suffix.lower() not in DEFAULT_LIMITS:
            continue
        if path.name in BANNED_FILENAMES:
            continue
        files.append(path)
    return sorted(files)


def load_budget_manifest(root: Path = ROOT) -> dict[str, Any]:
    manifest = load_json(root / MANIFEST_PATH.relative_to(ROOT))
    manifest.setdefault("critical_hotspots", {})
    manifest.setdefault("ratcheted_oversize_files", {})
    return manifest


def ratcheted_entries(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    combined: dict[str, dict[str, Any]] = {}
    for rel, entry in manifest.get("critical_hotspots", {}).items():
        combined[rel] = dict(entry or {})
    for rel, entry in manifest.get("ratcheted_oversize_files", {}).items():
        combined[rel] = dict(entry or {})
    return combined


def evaluate_ratcheted_file(rel: str, lines: int, max_lines: int) -> str | None:
    if lines > max_lines:
        return f"FAIL {rel}: {lines} lines exceeds ratchet budget {max_lines}"
    headroom = max_lines - lines
    tolerance = max(int(max_lines * 0.10), 15)
    if headroom > tolerance:
        return (
            f"FAIL {rel}: {lines} lines is below ratchet budget {max_lines}; "
            f"lower the manifest to {lines}"
        )
    return None
