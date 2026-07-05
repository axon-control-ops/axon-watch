"""Map canonical inbox items to KAIRO watch_rule semantics."""

from __future__ import annotations

_EXECUTE_ACTION_TYPES = frozenset({"dispatch", "retry", "review_changes"})
_APPROVAL_ACTION_TYPES = frozenset({"open_approvals"})


def _severity_urgency(severity: str) -> str:
    normalized = severity.strip().lower()
    if normalized in {"critical", "high"}:
        return "high"
    if normalized == "warning":
        return "medium"
    return "low"


def watch_rule_for_inbox_item(item: dict[str, object]) -> dict[str, object]:
    if isinstance(item.get("watch_rule"), dict):
        rule = dict(item["watch_rule"])
        rule.setdefault("mode", "observe")
        rule.setdefault("reason", "explicit_watch_rule")
        rule.setdefault("interrupts", False)
        return rule

    source = str(item.get("source", "watch")).strip().lower() or "watch"
    action_type = str(item.get("action_type", "none")).strip().lower() or "none"
    severity = str(item.get("severity", "info")).strip().lower() or "info"
    urgency = _severity_urgency(severity)

    if source == "approval" or action_type in _APPROVAL_ACTION_TYPES:
        return {
            "mode": "approval",
            "reason": "operator_approval_required",
            "interrupts": True,
        }

    if action_type in _EXECUTE_ACTION_TYPES and urgency == "high":
        return {
            "mode": "execute",
            "reason": "execution_requires_operator_review",
            "interrupts": True,
        }

    if urgency == "high":
        return {
            "mode": "advise",
            "reason": "high_urgency_signal",
            "interrupts": severity == "critical",
        }

    if urgency == "medium":
        return {
            "mode": "advise",
            "reason": "operator_should_review",
            "interrupts": False,
        }

    return {
        "mode": "observe",
        "reason": "ambient_watch_signal",
        "interrupts": False,
    }
