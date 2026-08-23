"""Cause-aware failure classification from receipts and error text."""

from __future__ import annotations

import re
from typing import Any

from app.fleet_self_heal.classify import classify_failure_signature
from app.platform_recovery.states import normalize_failure_class
from app.workspace_agents.failure_detail import (
    is_runtime_auth_failure,
    is_usage_limit_failure,
    normalize_operator_failure_detail,
)

_CLASS_MARKERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("PROVIDER_AUTH_FAILURE", ("unauthorized", "401", "invalid api key", "auth")),
    ("PROVIDER_RATE_LIMIT", ("rate limit", "429", "quota", "too many requests")),
    ("PROVIDER_TIMEOUT", ("timeout", "timed out", "deadline exceeded")),
    ("NETWORK_FAILURE", ("connection reset", "econnrefused", "network unreachable", "dns")),
    ("LEASE_EXPIRED", ("lease expired", "lease_holder", "already leased")),
    ("PROCESS_LOST", ("no such process", "pid ", "process disappeared", "worker dead")),
    ("HEARTBEAT_EXPIRED", ("heartbeat", "stale timeout", "no meaningful progress")),
    ("WORKTREE_FAILURE", ("worktree", "sandbox path", "no such sandbox")),
    ("DEPENDENCY_FAILURE", ("modulenotfound", "cannot find module", "lockfile")),
    ("TEST_FAILURE", ("pytest", "jest", "vitest", "assertionerror", "npm test")),
    ("VERIFIER_FAILURE", ("verification", "gate 6", "critical review")),
    ("CONFIGURATION_FAILURE", ("not configured", "missing env", "placeholder")),
    ("RESOURCE_EXHAUSTION", ("memoryerror", "enospc", "too many open files", "oom")),
)


def _haystack(*parts: object) -> str:
    return " ".join(str(part or "") for part in parts).strip().lower()


def classify_failure_class(
    *,
    detail: str = "",
    receipt_type: str = "",
    receipt_summary: str = "",
) -> str:
    raw = str(detail or "")
    normalized = normalize_operator_failure_detail(raw)
    hay = _haystack(raw, normalized, receipt_type, receipt_summary)

    # These are local orchestration and safety-gate failures, not provider
    # outages. Keep them ahead of generic history markers such as an older
    # timeout so Recovery Center never offers an unsafe automatic retry.
    if "linked task is missing" in hay:
        return "CONFIGURATION_FAILURE"
    if "private_company_material" in hay or "private company material" in hay:
        return "VERIFIER_FAILURE"
    if "cancelled by operator" in hay or "operator stopped" in hay:
        return "UNKNOWN"
    if "worker produced no changed files" in hay:
        return "VERIFIER_FAILURE"

    if is_runtime_auth_failure(raw) or is_runtime_auth_failure(normalized):
        return "PROVIDER_AUTH_FAILURE"
    if is_usage_limit_failure(raw) or is_usage_limit_failure(normalized):
        return "PROVIDER_RATE_LIMIT"

    signature = classify_failure_signature(detail=raw or receipt_summary)
    if signature.category == "gate_handled":
        if "auth" in hay or "credential" in hay:
            return "PROVIDER_AUTH_FAILURE"
        if "usage" in hay or "billing" in hay or "quota" in hay:
            return "PROVIDER_RATE_LIMIT"

    for failure_class, markers in _CLASS_MARKERS:
        if any(marker in hay for marker in markers):
            return failure_class

    if signature.category == "workspace_code":
        return "TEST_FAILURE"
    if signature.category == "fleet_infra":
        if "sandbox" in signature.subsystem or "worktree" in hay:
            return "WORKTREE_FAILURE"
        return "CONFIGURATION_FAILURE"
    return "UNKNOWN"


def classify_run_record(record: dict[str, Any], *, history: list[dict[str, Any]] | None = None) -> str:
    current = str(record.get("current_step") or "")
    current_haystack = current.lower()
    if "cancelled by operator" in current_haystack or "operator stopped" in current_haystack:
        return "UNKNOWN"
    current_class = classify_failure_class(detail=current)
    if current_class != "UNKNOWN":
        return current_class

    summaries: list[str] = []
    for item in history or []:
        receipt = item.get("receipt") if isinstance(item, dict) else None
        if not isinstance(receipt, dict):
            continue
        summaries.append(str(receipt.get("type") or ""))
        summaries.append(str(receipt.get("summary") or ""))
    return classify_failure_class(detail=" ".join(summaries))


_SECRET_RE = re.compile(r"(?i)(api[_-]?key|token|password|secret)\s*[:=]\s*\S+")


def redact_secrets(text: str) -> str:
    return _SECRET_RE.sub(r"\1=<redacted>", str(text or ""))


def normalize_class(value: str | None) -> str:
    return normalize_failure_class(value)
