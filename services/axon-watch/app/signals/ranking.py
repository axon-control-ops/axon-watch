"""Inbox ranking for watch-produced signals without mutating item schema.

Ordering follows the frozen planning rule stack in signal-events.md:

1. severity
2. recency (updated_at)
3. unresolved / attention state (status proxy)
4. operator-actionability (action_type)
5. workspace priority (watch-owned config, not inbox schema)
"""

from __future__ import annotations

_SEVERITY_RANK = {
    "critical": 0,
    "high": 1,
    "warning": 2,
    "info": 3,
}

# Lower rank means the signal still needs operator attention.
_STATUS_RANK = {
    "open": 0,
    "watching": 1,
    "failed_delivery": 2,
    "acknowledged": 3,
    "suppressed": 4,
    "resolved": 5,
}

# Lower rank means the signal suggests a more urgent operator action.
_ACTION_TYPE_RANK = {
    "open_approvals": 0,
    "review_changes": 1,
    "dispatch": 2,
    "investigate": 3,
    "retry": 4,
    "open_workspace": 5,
    "open_dashboard": 6,
    "resolve": 7,
    "none": 8,
}

# Watch-owned workspace priority hints. Does not change inbox item schema.
_WORKSPACE_PRIORITY = {
    "workspace_bootstrap": 0,
    "workspace_alpha": 1,
}

_DEFAULT_WORKSPACE_PRIORITY = 5
_UNKNOWN_RANK = 99


def severity_rank(severity: str) -> int:
    return _SEVERITY_RANK.get(severity, _UNKNOWN_RANK)


def status_rank(status: str) -> int:
    return _STATUS_RANK.get(status, _UNKNOWN_RANK)


def action_type_rank(action_type: str) -> int:
    return _ACTION_TYPE_RANK.get(action_type, _UNKNOWN_RANK)


def workspace_priority_rank(workspace_id: str) -> int:
    return _WORKSPACE_PRIORITY.get(workspace_id, _DEFAULT_WORKSPACE_PRIORITY)


def _signal_id_tiebreak(item: dict[str, object]) -> str:
    return str(item.get("signal_id", ""))


def rank_inbox_items(items: list[dict[str, object]]) -> list[dict[str, object]]:
    # Stable multi-pass ordering: least important key first, severity last.
    ranked = sorted(items, key=_signal_id_tiebreak)
    ranked = sorted(
        ranked,
        key=lambda item: str(item.get("updated_at", "")),
        reverse=True,
    )
    ranked = sorted(
        ranked,
        key=lambda item: workspace_priority_rank(str(item.get("workspace_id", ""))),
    )
    ranked = sorted(
        ranked,
        key=lambda item: action_type_rank(str(item.get("action_type", "none"))),
    )
    ranked = sorted(
        ranked,
        key=lambda item: status_rank(str(item.get("status", ""))),
    )
    return sorted(
        ranked,
        key=lambda item: severity_rank(str(item.get("severity", ""))),
    )
