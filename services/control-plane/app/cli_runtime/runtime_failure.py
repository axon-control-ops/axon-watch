"""Truthful fallback copy for unavailable versus crashed CLI runtimes."""

from __future__ import annotations

from app.workspace_agents.failure_detail import (
    is_billing_block_failure,
    is_runtime_auth_failure,
    is_usage_limit_failure,
)


def runtime_unready_reason(record: dict[str, object]) -> str:
    runtime_id = str(record.get("id") or "runtime")
    label = str(record.get("label") or runtime_id)
    target_type = str(record.get("target_type") or "local")
    if target_type == "cloud" or not record.get("available"):
        return f"{label} unavailable"
    auth = record.get("auth") if isinstance(record.get("auth"), dict) else {}
    message = str(auth.get("message") or "").strip()
    if message and not auth.get("logged_in"):
        return message
    return f"{label} unavailable"


def _operator_next_step(reason: str) -> str:
    """Advice must match the real blocker — never default every failure to vault."""
    lowered = reason.lower()
    if is_billing_block_failure(reason):
        return (
            "Pay the unpaid Cursor invoice at cursor.com/dashboard (Stripe), "
            "then retry. Do not raise usage/spend caps for this."
        )
    if is_usage_limit_failure(reason):
        return (
            "Check Cursor Usage in Settings → CLI runtime — Auto+Composer may still "
            "have headroom or on-demand spend. Then retry."
        )
    # Auth-probe timeouts are host CLI health, not vault unlock.
    if "auth probe" in lowered:
        return "Check `cursor agent status` on the host, then retry."
    if is_runtime_auth_failure(reason):
        return "Run `cursor agent login` on the host or unlock `/vault`, then retry."
    if "timed out" in lowered:
        return "Check `cursor agent status` on the host, then retry."
    return "Check Runtime status, then retry."


def fallback_reply(
    *,
    composer_mode: str,
    user_prompt: str,
    context_block: str,
    reason: str,
    failure_phase: str = "not_ready",
    runtime_label: str = "",
) -> str:
    del user_prompt, context_block
    next_step = _operator_next_step(reason)
    if failure_phase == "run_error":
        label = (runtime_label or "the selected CLI runtime").strip()
        if is_billing_block_failure(reason) or is_usage_limit_failure(reason):
            return (
                f"Lane B ({composer_mode}) could not start on {label}: {reason}. "
                f"{next_step}"
            )
        return (
            f"Lane B ({composer_mode}) failed on {label}: {reason}. "
            f"{next_step}"
        )
    if is_billing_block_failure(reason):
        return (
            f"Lane B ({composer_mode}) could not start — Cursor unpaid invoice blocked the agent: "
            f"{reason}. {next_step}"
        )
    if is_usage_limit_failure(reason):
        return (
            f"Lane B ({composer_mode}) could not start — Cursor usage limits blocked the agent: "
            f"{reason}. {next_step}"
        )
    return (
        f"Lane B ({composer_mode}) cannot start because no CLI runtime is ready: {reason}. "
        f"{next_step}"
    )


__all__ = ["fallback_reply", "runtime_unready_reason"]
