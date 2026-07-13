"""Post-run checks that flag unverified completion claims in Lane B replies."""

from __future__ import annotations

import re
from pathlib import Path

_EDIT_BLOCK_RE = re.compile(r":::edit\s+(\S+)", re.MULTILINE)
_CLAIM_PATTERNS = (
    re.compile(r"\b(?:I(?:'ve| have)?|Successfully)\s+(?:committed|edited|created|updated|saved|switched|pushed)\b", re.I),
    re.compile(r"\b(?:Committed|Pushed|Saved|Updated|Created|Switched)\s+(?:successfully|to)\b", re.I),
    re.compile(r"\bExplorer and terminal now use\b", re.I),
)


def extract_edit_paths(content: str) -> list[str]:
    return list(dict.fromkeys(_EDIT_BLOCK_RE.findall(content or "")))


def scan_unverified_claims(content: str, *, execution_tier: str) -> list[str]:
    warnings: list[str] = []
    text = content or ""
    edit_paths = extract_edit_paths(text)
    has_claim = any(pattern.search(text) for pattern in _CLAIM_PATTERNS)

    if execution_tier == "consultative" and has_claim:
        warnings.append(
            "consultative tier: reply contains past-tense execution claims without Full Access"
        )

    if has_claim and not edit_paths and ":::terminal" not in text:
        if re.search(r"\b(?:edited|saved|updated|created)\b", text, re.I):
            warnings.append("reply claims file changes but no edit receipts were recorded")

    # Git commits via workspace_git emit :::terminal receipts — treat as verified.
    if (
        re.search(r"\bCommitted successfully\b", text, re.I)
        and ":::terminal" in text
        and re.search(r"git commit", text, re.I)
    ):
        warnings = [
            item
            for item in warnings
            if "past-tense execution claims" not in item
        ]

    if re.search(r"\b(?:web consensus|Healthline|Allrecipes|according to online)\b", text, re.I):
        if ":::research" not in text:
            warnings.append("reply cites online sources without a research receipt block")

    return warnings


def verify_edit_paths(workspace_root: Path, paths: list[str], *, run_started_epoch: float) -> list[str]:
    warnings: list[str] = []
    for relative in paths:
        candidate = (workspace_root / relative).resolve()
        if not candidate.is_file():
            warnings.append(f"edit receipt path missing on disk: {relative}")
            continue
        if candidate.stat().st_mtime + 1 < run_started_epoch:
            warnings.append(f"edit receipt path not modified during this run: {relative}")
    return warnings


def build_verification_notice(warnings: list[str]) -> str:
    if not warnings:
        return ""
    lines = [
        "",
        "---",
        "**Verification notice:** this reply contains claims that could not be fully verified:",
    ]
    lines.extend(f"- {item}" for item in warnings)
    lines.append("Treat completion statements as unverified until receipts confirm them.")
    return "\n".join(lines)


def verify_lane_b_reply(
    content: str,
    *,
    execution_tier: str,
    workspace_root: Path | None = None,
    run_started_epoch: float | None = None,
) -> tuple[str, list[str]]:
    warnings = scan_unverified_claims(content, execution_tier=execution_tier)
    if workspace_root is not None and run_started_epoch is not None:
        warnings.extend(
            verify_edit_paths(
                workspace_root,
                extract_edit_paths(content),
                run_started_epoch=run_started_epoch,
            )
        )
    notice = build_verification_notice(warnings)
    if notice:
        return f"{content.rstrip()}{notice}", warnings
    return content, warnings
