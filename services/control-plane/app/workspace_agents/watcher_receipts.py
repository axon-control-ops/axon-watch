"""Surface the newest watcher receipts (CiWatch/DeployWatch/…) to reporting agents.

Watchers drop JSON receipts into ``docs/ops/agent-reports/`` in the bound
project root. Those files are typically untracked, so a worker running in an
isolation checkout cannot see them — which is how a Lead status shift ends up
reporting "no live CI signal" while a P1 red-build receipt sits on disk.

The control plane reads them from the live project root and injects a compact,
age-labelled block into the prompt.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

RECEIPT_DIRNAME = "docs/ops/agent-reports"
# Severity ranking for display order; unknown severities sort last.
_SEVERITY_ORDER = {"p0": 0, "p1": 1, "p2": 2, "p3": 3, "p4": 4}
_OK_STATUSES = frozenset({"ok", "pass", "passed", "green", "healthy"})
# Newest-first scan bound: the directory accumulates months of receipts.
_MAX_SCAN_FILES = 60
# Enough for a full watcher fleet, so a green DeployWatch is not crowded out by
# the failing ones it needs to be read alongside.
_MAX_ITEMS = 8
# Past this age a receipt describes history, not "right now".
_STALE_AFTER_HOURS = 12.0
# Roles that report on system state rather than only changing code.
_RECEIPT_ROLES = frozenset({"lead", "watcher"})
_STATUS_GOAL_RE = re.compile(
    r"\b(status|health|healthy|current state|how is|red|green|ci signal|"
    r"production|deploy(?:ment)?s?)\b",
    re.IGNORECASE,
)


# Bubblewrap rewrites HOME and does not carry the operator's gh credentials
# (the token lives in the desktop keyring, which the sandbox cannot reach), so
# an in-sandbox `gh` reports "not logged in" no matter what the policy permits.
GH_ROUTING_NOTE = (
    "For a fresher reading than these receipts, run gh through the host helper — "
    "`axon-agent-terminal-job --workspace <workspace_id> -- gh run list` — not directly: "
    "inside the sandbox gh has no credentials and will say it is not logged in. "
    "That is an environment limit, not evidence that CI is healthy."
)


def chat_watcher_receipts_section(workspace_id: str, user_prompt: str) -> str:
    """Receipts block for a plain chat turn (no leased task, no role binding).

    Chat runs from the project root but still cannot discover untracked watcher
    receipts, so a status question here needs the same evidence a shift gets.
    """
    if not str(workspace_id or "").strip():
        return ""
    if not should_attach_watcher_receipts(role="", goal=user_prompt):
        return ""
    block = watcher_receipts_prompt_block(workspace_id)
    return f"\n\n{block}" if block else ""


def should_attach_watcher_receipts(*, role: str, goal: str) -> bool:
    """Reporting roles always; any role asked 'how is it doing right now'."""
    if str(role or "").strip().lower() in _RECEIPT_ROLES:
        return True
    return bool(_STATUS_GOAL_RE.search(str(goal or "")))


@dataclass(frozen=True)
class WatcherReceipt:
    agent: str
    status: str
    severity: str
    summary: str
    observed_at: datetime | None
    filename: str
    needs_operator: bool = False

    @property
    def is_ok(self) -> bool:
        return self.status.strip().lower() in _OK_STATUSES

    def age_hours(self, now: datetime) -> float | None:
        if self.observed_at is None:
            return None
        return max(0.0, (now - self.observed_at).total_seconds() / 3600.0)


def _parse_timestamp(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _receipt_from_payload(
    payload: dict[str, Any],
    *,
    filename: str,
    mtime: float,
) -> WatcherReceipt | None:
    agent = str(payload.get("agent") or "").strip()
    if not agent:
        return None
    observed_at = None
    for key in ("run_id", "generated_at", "timestamp", "completed_at"):
        observed_at = _parse_timestamp(payload.get(key))
        if observed_at is not None:
            break
    if observed_at is None:
        observed_at = datetime.fromtimestamp(mtime, tz=timezone.utc)
    return WatcherReceipt(
        agent=agent,
        status=str(payload.get("status") or "unknown").strip(),
        severity=str(payload.get("severity") or "").strip(),
        summary=str(payload.get("summary") or "").strip(),
        observed_at=observed_at,
        filename=filename,
        needs_operator=bool(payload.get("needs_operator")),
    )


def receipts_dir_for_workspace(workspace_id: str) -> Path | None:
    """Live project root's receipt dir — deliberately not the isolation checkout."""
    from app.terminal.workspace_roots import resolve_workspace_root

    try:
        root = Path(resolve_workspace_root(workspace_id))
    except Exception:  # noqa: BLE001 - unbound workspace is not an error here
        return None
    candidate = root / RECEIPT_DIRNAME
    return candidate if candidate.is_dir() else None


def load_latest_watcher_receipts(
    workspace_id: str,
    *,
    limit: int = _MAX_ITEMS,
) -> list[WatcherReceipt]:
    """Newest receipt per watcher agent, worst severity first."""
    directory = receipts_dir_for_workspace(workspace_id)
    if directory is None:
        return []
    try:
        entries = [
            entry
            for entry in os.scandir(directory)
            if entry.is_file() and entry.name.endswith(".json")
        ]
    except OSError:
        return []

    entries.sort(key=lambda entry: entry.stat().st_mtime, reverse=True)
    newest_by_agent: dict[str, WatcherReceipt] = {}
    for entry in entries[:_MAX_SCAN_FILES]:
        try:
            payload = json.loads(Path(entry.path).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(payload, dict):
            continue
        receipt = _receipt_from_payload(
            payload,
            filename=entry.name,
            mtime=entry.stat().st_mtime,
        )
        # Entries are newest-first, so the first hit per agent is the newest.
        if receipt is not None and receipt.agent not in newest_by_agent:
            newest_by_agent[receipt.agent] = receipt

    def _rank(receipt: WatcherReceipt) -> tuple[int, int, float]:
        severity_rank = _SEVERITY_ORDER.get(receipt.severity.strip().lower(), 9)
        observed = receipt.observed_at.timestamp() if receipt.observed_at else 0.0
        return (0 if not receipt.is_ok else 1, severity_rank, -observed)

    return sorted(newest_by_agent.values(), key=_rank)[: max(0, int(limit))]


def _format_age(receipt: WatcherReceipt, now: datetime) -> str:
    age = receipt.age_hours(now)
    if age is None:
        return "age unknown"
    if age < 1.0:
        label = f"{int(age * 60)}m ago"
    elif age < 48.0:
        label = f"{age:.0f}h ago"
    else:
        label = f"{age / 24:.0f}d ago"
    return f"{label}{' — STALE, not current' if age > _STALE_AFTER_HOURS else ''}"


def watcher_receipts_prompt_block(
    workspace_id: str,
    *,
    now: datetime | None = None,
    limit: int = _MAX_ITEMS,
) -> str:
    """Render the receipts block, or an explicit 'none found' line."""
    moment = now or datetime.now(timezone.utc)
    receipts = load_latest_watcher_receipts(workspace_id, limit=limit)
    directory = receipts_dir_for_workspace(workspace_id)
    if not receipts:
        if directory is None:
            return ""
        return (
            "LIVE WATCHER RECEIPTS: none found in the project root's "
            f"`{RECEIPT_DIRNAME}/`. Say that the watchers have not reported, "
            "rather than implying the services themselves are healthy."
        )

    lines = [
        "LIVE WATCHER RECEIPTS (read from the bound project root, NOT your "
        f"isolation checkout — these files are usually untracked, so `ls`/`git` "
        f"inside your checkout will not show them). Source: `{RECEIPT_DIRNAME}/`.",
    ]
    for receipt in receipts:
        severity = f" {receipt.severity}" if receipt.severity else ""
        summary = receipt.summary or "(no summary)"
        operator = " · needs_operator" if receipt.needs_operator else ""
        lines.append(
            f"- {receipt.agent}: {receipt.status}{severity}{operator} — {summary} "
            f"[{_format_age(receipt, moment)}; `{RECEIPT_DIRNAME}/{receipt.filename}`]"
        )
    lines.append(
        "Use these as your live CI/deploy/runtime signal and cite the receipt "
        "file you relied on. Do not report 'no live signal available' without "
        "first accounting for every line above, and do not present a receipt "
        "marked STALE as the current state — say how old it is."
    )
    lines.append(GH_ROUTING_NOTE)
    return "\n".join(lines)


__all__ = [
    "RECEIPT_DIRNAME",
    "WatcherReceipt",
    "load_latest_watcher_receipts",
    "receipts_dir_for_workspace",
    "chat_watcher_receipts_section",
    "should_attach_watcher_receipts",
    "watcher_receipts_prompt_block",
]
