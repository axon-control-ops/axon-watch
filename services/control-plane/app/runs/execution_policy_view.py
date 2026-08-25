"""Report the execution policy a run actually resolved.

The dock had no structured source for this, so it inferred the access pill from
the composer's Sandbox toggle — which made every thread read "FULL ACCESS",
including watcher threads that resolved to consultative and fleet-worker threads
whose writes were narrowed to a handful of role paths. The truth is already
recorded per run as an ``agent_execution_policy`` receipt; this parses the latest
one back into data so the UI can stop guessing.
"""

from __future__ import annotations

import re
from typing import Any

_ACCESS_RE = re.compile(r"access=(?P<access>[\w-]+)")
_WRITES_RE = re.compile(r"writes=(?P<writes>\S+)")
_NETWORK_RE = re.compile(r"network=(?P<network>[\w-]+)")

READ_ONLY_MARKER = "read-only"


def parse_execution_policy_summary(summary: str) -> dict[str, Any] | None:
    """Parse one ``agent_execution_policy`` receipt summary into structured data."""
    text = str(summary or "")
    access_match = _ACCESS_RE.search(text)
    if access_match is None:
        return None
    writes_match = _WRITES_RE.search(text)
    raw_writes = writes_match.group("writes") if writes_match else READ_ONLY_MARKER
    write_paths = (
        []
        if raw_writes == READ_ONLY_MARKER
        else [part for part in raw_writes.split(",") if part]
    )
    network_match = _NETWORK_RE.search(text)
    return {
        "execution_access": access_match.group("access"),
        "write_paths": write_paths,
        "read_only": not write_paths,
        "network_mode": network_match.group("network") if network_match else "",
    }


def run_execution_policy(run_id: str) -> dict[str, Any]:
    """Latest resolved policy for a run, or an explicit unknown.

    Unknown is a real state — a queued run has not resolved a policy yet — and
    the caller must be able to tell it apart from "full", rather than defaulting
    to the most permissive label.
    """
    from app.runs.service import get_run_history

    history = get_run_history(run_id)
    latest: dict[str, Any] | None = None
    for item in history.get("items") or []:
        receipt = item.get("receipt") if isinstance(item, dict) else None
        if not isinstance(receipt, dict):
            continue
        if str(receipt.get("type") or "") != "agent_execution_policy":
            continue
        parsed = parse_execution_policy_summary(str(receipt.get("summary") or ""))
        if parsed is not None:
            latest = parsed
    if latest is None:
        return {"run_id": run_id, "known": False, "execution_access": "unknown"}
    return {"run_id": run_id, "known": True, **latest}


__all__ = ["parse_execution_policy_summary", "run_execution_policy"]
