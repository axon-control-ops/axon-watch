#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
from datetime import date
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
WAIVER_PATH = ROOT / "docs/engineering/guardrail-waivers.json"


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


def evaluate_critical_hotspot_change(
    rel: str,
    *,
    lines: int,
    budget: int,
    has_active_waiver: bool,
) -> str | None:
    if lines > budget:
        return (
            f"FAIL {rel}: changed critical hotspot exceeds ratchet budget "
            f"{budget} at {lines} lines"
        )
    if lines == budget and not has_active_waiver:
        return (
            f"FAIL {rel}: critical hotspot changed without shrinking below "
            f"ratchet budget {budget}; extract in the same patch or add an "
            f"active waiver"
        )
    return None


def load_waiver_register(root: Path = ROOT) -> dict[str, Any]:
    path = root / WAIVER_PATH.relative_to(ROOT)
    if not path.is_file():
        return {"version": 1, "waivers": []}
    return load_json(path)


def active_waiver_files(
    register: dict[str, Any],
    critical_paths: dict[str, Any],
    *,
    today: date | None = None,
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    now = today or date.today()
    active: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    waivers = register.get("waivers", [])
    if not isinstance(waivers, list):
        return active, [f"FAIL {WAIVER_PATH.relative_to(ROOT)}: `waivers` must be a list"]
    for index, entry in enumerate(waivers):
        if not isinstance(entry, dict):
            errors.append(
                f"FAIL {WAIVER_PATH.relative_to(ROOT)}: waiver #{index + 1} must be an object"
            )
            continue
        rel = str(entry.get("file") or "").strip()
        reason = str(entry.get("reason") or "").strip()
        expiry_raw = str(entry.get("expiry") or "").strip()
        follow_up = str(entry.get("follow_up") or "").strip()
        if not rel or not reason or not expiry_raw or not follow_up:
            errors.append(
                f"FAIL {WAIVER_PATH.relative_to(ROOT)}: waiver #{index + 1} requires "
                f"file, reason, expiry, and follow_up"
            )
            continue
        if rel not in critical_paths:
            errors.append(
                f"FAIL {WAIVER_PATH.relative_to(ROOT)}: waiver for `{rel}` is invalid "
                f"because it is not a critical hotspot"
            )
            continue
        try:
            expiry = date.fromisoformat(expiry_raw)
        except ValueError:
            errors.append(
                f"FAIL {WAIVER_PATH.relative_to(ROOT)}: waiver for `{rel}` has invalid "
                f"expiry `{expiry_raw}`"
            )
            continue
        if expiry < now:
            errors.append(
                f"FAIL {WAIVER_PATH.relative_to(ROOT)}: waiver for `{rel}` expired on "
                f"{expiry.isoformat()}"
            )
            continue
        active[rel] = entry
    return active, errors


def _git_ref_exists(root: Path, ref: str) -> bool:
    if not ref:
        return False
    try:
        subprocess.check_output(
            ["git", "rev-parse", "--verify", ref],
            cwd=root,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def detect_compare_range(root: Path = ROOT) -> str:
    explicit = str(os.getenv("GUARDRAIL_COMPARE_RANGE") or "").strip()
    if explicit:
        return explicit

    base_sha = str(os.getenv("GITHUB_BASE_SHA") or "").strip()
    if _git_ref_exists(root, base_sha):
        return f"{base_sha}...HEAD"

    base_ref = str(os.getenv("GITHUB_BASE_REF") or "").strip()
    remote_ref = f"origin/{base_ref}" if base_ref else ""
    if _git_ref_exists(root, remote_ref):
        return f"{remote_ref}...HEAD"

    if _git_ref_exists(root, "HEAD~1"):
        return "HEAD~1...HEAD"

    return ""


def changed_files(root: Path = ROOT, compare_range: str = "") -> set[str]:
    if compare_range:
        output = subprocess.check_output(
            ["git", "diff", "--name-only", "--diff-filter=ACMRTUXB", compare_range, "--"],
            cwd=root,
            text=True,
        )
        return {line.strip() for line in output.splitlines() if line.strip()}

    staged = subprocess.check_output(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMRTUXB", "--"],
        cwd=root,
        text=True,
    )
    unstaged = subprocess.check_output(
        ["git", "diff", "--name-only", "--diff-filter=ACMRTUXB", "--"],
        cwd=root,
        text=True,
    )
    return {
        line.strip()
        for line in (staged + "\n" + unstaged).splitlines()
        if line.strip()
    }
