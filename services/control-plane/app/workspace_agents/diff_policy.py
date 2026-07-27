"""Gate 6 diff / secret / scope policy for acceptance evidence."""

from __future__ import annotations

import re
from dataclasses import dataclass
from fnmatch import fnmatch
from typing import Iterable

SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"(?i)api[_-]?key\s*[:=]\s*['\"][^'\"]{12,}['\"]"),
)


@dataclass(frozen=True)
class DiffPolicyFinding:
    code: str
    path: str
    detail: str


def path_allowed(path: str, allowed_paths: Iterable[str]) -> bool:
    normalized = path.lstrip("./")
    allowed = list(allowed_paths)
    if not allowed:
        return True
    return any(
        normalized == prefix.rstrip("/")
        or normalized.startswith(prefix if prefix.endswith("/") else prefix + "/")
        for prefix in allowed
    )


def normalize_path_prefixes(paths: Iterable[str]) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for raw in paths:
        prefix = str(raw or "").strip().lstrip("./")
        if not prefix:
            continue
        key = prefix.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(prefix)
    return cleaned


def resolve_effective_allowed_paths(
    *,
    contract_allowed_paths: Iterable[str] | None = None,
    task_allowed_paths: Iterable[str] | None = None,
) -> list[str]:
    """Intersect repo contract scope with per-task write scope.

    Missing task scope falls back to the contract (or empty = unrestricted by
    path allowlist). When both are present, a path must satisfy both prefixes.
    """
    contract = normalize_path_prefixes(contract_allowed_paths or [])
    task = normalize_path_prefixes(task_allowed_paths or [])
    if not task:
        return contract
    if not contract:
        return task
    effective: list[str] = []
    seen: set[str] = set()
    for left in task:
        for right in contract:
            if path_allowed(left, [right]):
                candidate = left
            elif path_allowed(right, [left]):
                candidate = right
            else:
                continue
            key = candidate.lower()
            if key in seen:
                continue
            seen.add(key)
            effective.append(candidate)
    if not effective:
        # Both scopes present but disjoint — deny all paths (never fail open).
        return ["__axon_deny_all__"]
    return effective


def path_forbidden(path: str, forbidden_globs: Iterable[str]) -> bool:
    normalized = path.lstrip("./")
    for pattern in forbidden_globs:
        if fnmatch(normalized, pattern):
            return True
        # Also match when the pattern assumes a **/ prefix but the path is rooted.
        if pattern.startswith("**/") and fnmatch(normalized, pattern[3:]):
            return True
        if pattern.endswith("/**") and (
            normalized == pattern[:-3]
            or normalized.startswith(pattern[:-3].rstrip("*").rstrip("/") + "/")
        ):
            return True
    return False


def scan_text_for_secrets(text: str) -> list[str]:
    hits: list[str] = []
    for pattern in SECRET_PATTERNS:
        if pattern.search(text or ""):
            hits.append(pattern.pattern)
    return hits


def evaluate_changed_paths(
    changed_paths: Iterable[str],
    *,
    allowed_paths: Iterable[str],
    forbidden_path_globs: Iterable[str],
    max_paths: int = 80,
) -> list[DiffPolicyFinding]:
    findings: list[DiffPolicyFinding] = []
    paths = [str(p).lstrip("./") for p in changed_paths if str(p).strip()]
    if len(paths) > max_paths:
        findings.append(
            DiffPolicyFinding(
                code="diff_budget",
                path="*",
                detail=f"changed path count {len(paths)} exceeds budget {max_paths}",
            )
        )
    for path in paths:
        if path_forbidden(path, forbidden_path_globs):
            findings.append(
                DiffPolicyFinding(
                    code="forbidden_path",
                    path=path,
                    detail="path matches forbidden glob",
                )
            )
        elif not path_allowed(path, allowed_paths):
            findings.append(
                DiffPolicyFinding(
                    code="out_of_scope",
                    path=path,
                    detail="path outside allowed_paths",
                )
            )
    return findings


def evaluate_diff_texts(
    path_to_text: dict[str, str],
) -> list[DiffPolicyFinding]:
    findings: list[DiffPolicyFinding] = []
    for path, text in path_to_text.items():
        for pattern in scan_text_for_secrets(text):
            findings.append(
                DiffPolicyFinding(
                    code="secret",
                    path=path,
                    detail=f"matched secret pattern: {pattern}",
                )
            )
    return findings
