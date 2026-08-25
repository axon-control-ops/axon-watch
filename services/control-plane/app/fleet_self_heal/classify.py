"""Classify fleet run failures: gate-handled vs. fleet-infra bug vs. workspace code.

Fills the gap noted this session: none of the existing failure_detail.py
classifiers aggregate into a single "what kind of failure is this, and is it
axon-watch's own bug" answer — each caller chains them ad hoc. This module is
that aggregator, purpose-built for VAXON fleet self-heal's dispatch decision.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from app.workspace_agents.failure_detail import (
    is_billing_block_failure,
    is_billing_failure,
    is_runtime_auth_failure,
    is_shift_continuation_failure,
    is_usage_limit_failure,
    normalize_operator_failure_detail,
)

# A crash stack-framed inside axon-watch's own control-plane package is, by
# definition, axon-watch's own bug — not the target workspace's code. Line
# numbers are captured but never used in the fingerprint (they drift across
# fix commits); only the file path is a stable identity.
_CP_TRACEBACK_RE = re.compile(
    r'File "[^"]*?(services/control-plane/app/[\w/]+\.py)", line (\d+)'
)

# (marker substring, subsystem, file_hint) — seeded from the two real fleet
# bugs root-caused and fixed this session, plus generic dispatch/sandbox
# vocabulary. Extend this table as new fleet-infra failure phrasings are
# confirmed; do not guess a marker from a single unconfirmed occurrence.
_FLEET_INFRA_MARKERS: tuple[tuple[str, str, str], ...] = (
    ("could not resolve sandbox path", "sandbox_resolution", "app/workspace_agents/agent_sandbox.py"),
    ("no such sandbox root", "sandbox_resolution", "app/cli_runtime/catalog_discovery.py"),
    ("sandbox_policy_adapter", "sandbox_policy", "app/cli_runtime/sandbox_policy_adapter.py"),
    ("sandbox checkout toolchain is not runnable", "sandbox_toolchain", "app/cli_runtime/agent_dispatch_preflight.py"),
    ("can't create file at", "sandbox_bwrap_bind", "app/cli_runtime/agent_sandbox_paths.py"),
    ("jest: not found", "sandbox_node_modules", "app/cli_runtime/sandbox_preview.py"),
    ("mcp.json", "mcp_adapter", "app/cli_runtime/research_mcp.py"),
    ("maximum recursion depth exceeded", "cursor_recursion", "app/cli_runtime/cursor_agent.py"),
    ("could not install cursor-agent", "cli_install", "app/cli_runtime/cursor_agent.py"),
    ("continuous worker dispatch failed", "dispatch_generic", "app/workspace_agents/worker_dispatch.py"),
)

# Failures that already look like normal task/acceptance-criteria misses,
# not a fleet-infra bug — stays with the existing per-workspace attend loop.
_WORKSPACE_CODE_MARKERS = (
    "acceptance=fail",
    "critical review",
    "confidence:",
)


@dataclass(frozen=True)
class FailureSignature:
    category: str  # "gate_handled" | "fleet_infra" | "workspace_code" | "unknown"
    fingerprint: str  # stable dedupe key; "" for gate_handled/workspace_code/unknown
    subsystem: str
    file_hint: str
    marker: str
    confidence: str  # "high" (traceback path) | "medium" (phrase marker) | "low"
    raw_detail: str


def build_fingerprint(*, subsystem: str, marker: str, file_hint: str) -> str:
    basis = f"{subsystem}:{file_hint or 'unknown-file'}:{marker}"
    digest = hashlib.sha256(basis.encode("utf-8")).hexdigest()[:16]
    return f"fleetbug:{subsystem}:{digest}"


def _subsystem_from_path(file_hint: str) -> str:
    parts = [part for part in file_hint.split("/") if part]
    # services/control-plane/app/<pkg>/<module>.py -> "<pkg>.<module>"
    try:
        app_index = parts.index("app")
    except ValueError:
        return "unknown"
    tail = parts[app_index + 1 :]
    if not tail:
        return "unknown"
    module = tail[-1].removesuffix(".py")
    package = tail[0] if len(tail) > 1 else module
    return f"{package}.{module}" if package != module else module


def _is_gate_handled(detail: str) -> bool:
    return (
        is_usage_limit_failure(detail)
        or is_billing_block_failure(detail)
        or is_billing_failure(detail)
        or is_runtime_auth_failure(detail)
        or is_shift_continuation_failure(detail)
    )


def classify_failure_signature(*, detail: str) -> FailureSignature:
    raw = str(detail or "")
    normalized = normalize_operator_failure_detail(raw)

    if _is_gate_handled(raw) or _is_gate_handled(normalized):
        return FailureSignature(
            category="gate_handled", fingerprint="", subsystem="", file_hint="",
            marker="", confidence="high", raw_detail=raw,
        )

    traceback_match = _CP_TRACEBACK_RE.search(raw)
    if traceback_match:
        file_hint = traceback_match.group(1)
        subsystem = _subsystem_from_path(file_hint)
        marker = f"traceback:{file_hint}"
        fingerprint = build_fingerprint(subsystem=subsystem, marker=marker, file_hint=file_hint)
        return FailureSignature(
            category="fleet_infra", fingerprint=fingerprint, subsystem=subsystem,
            file_hint=file_hint, marker=marker, confidence="high", raw_detail=raw,
        )

    hay = f"{raw} {normalized}".lower()
    for marker, subsystem, file_hint in _FLEET_INFRA_MARKERS:
        if marker in hay:
            fingerprint = build_fingerprint(subsystem=subsystem, marker=marker, file_hint=file_hint)
            return FailureSignature(
                category="fleet_infra", fingerprint=fingerprint, subsystem=subsystem,
                file_hint=file_hint, marker=marker, confidence="medium", raw_detail=raw,
            )

    if any(marker in hay for marker in _WORKSPACE_CODE_MARKERS):
        return FailureSignature(
            category="workspace_code", fingerprint="", subsystem="", file_hint="",
            marker="", confidence="low", raw_detail=raw,
        )

    return FailureSignature(
        category="unknown", fingerprint="", subsystem="", file_hint="",
        marker="", confidence="low", raw_detail=raw,
    )


def quick_fleet_infra_marker_match(detail: str) -> bool:
    """Cheap phrase-only check usable on already-truncated (e.g. 180-char)
    detail strings; does NOT do traceback-path scanning. Used by
    lead_checkin_assign.py to keep the generic attend loop from dispatching a
    dead-end fix for a bug that isn't in the failing workspace's own repo."""
    if _is_gate_handled(detail):
        return False
    hay = str(detail or "").lower()
    return any(marker in hay for marker, _subsystem, _hint in _FLEET_INFRA_MARKERS)


__all__ = [
    "FailureSignature",
    "build_fingerprint",
    "classify_failure_signature",
    "quick_fleet_infra_marker_match",
]
