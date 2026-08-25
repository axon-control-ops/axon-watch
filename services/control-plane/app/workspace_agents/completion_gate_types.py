"""Shared result types for worker completion/delivery gates."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CompletionGateResult:
    passed: bool
    reason: str
    changed_paths: list[str]
    expected_files: list[str]
    validation_status: str
    commit_sha: str = ""


@dataclass(frozen=True)
class WorkerDeliveryGateOutcome:
    passed: bool
    reason: str
    publish: Any | None = None
    preserve_isolation: bool = False
    preflight_reason: str = ""
