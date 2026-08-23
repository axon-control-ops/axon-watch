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
        if "codex" in lowered:
            return (
                "The Codex CLI reported a usage-limit block; Axon cannot inspect the live "
                "account quota. Retry once, or switch this workspace to Claude/Cursor."
            )
        if "claude" in lowered:
            return (
                "The Claude CLI reported a usage-limit block; Axon cannot inspect the live "
                "account quota. Retry once, or switch this workspace to Codex/Cursor."
            )
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


# Every fallback_reply() branch opens with "Lane B (<mode>) " followed by one
# of these verbs. The console keys its "this reply is a runtime failure, not an
# answer" styling off the same shape (see
# apps/console-web/src/lib/thread-message-view.ts::agentContentLooksLikeRuntimeFallback).
# A fallback is delivered as an ordinary assistant message, so without this the
# operator cannot tell a failure from a real answer without reading it closely.
# tests/test_runtime_fallback_marker_contract.py pins both sides together —
# if you reword these strings, update the console detector in the same change.
RUNTIME_FALLBACK_PREFIX = "Lane B ("
RUNTIME_FALLBACK_VERBS: tuple[str, ...] = (
    "failed on ",
    "could not start",
    "cannot start because",
)


def looks_like_runtime_fallback(content: str) -> bool:
    """True when text is a fallback_reply() rather than a real agent answer."""
    text = " ".join(str(content or "").split())
    if not text.startswith(RUNTIME_FALLBACK_PREFIX):
        return False
    return any(verb in text for verb in RUNTIME_FALLBACK_VERBS)


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
            f"Lane B ({composer_mode}) could not start — the selected runtime's usage limit blocked the agent: "
            f"{reason}. {next_step}"
        )
    return (
        f"Lane B ({composer_mode}) cannot start because no CLI runtime is ready: {reason}. "
        f"{next_step}"
    )


__all__ = [
    "RUNTIME_FALLBACK_PREFIX",
    "RUNTIME_FALLBACK_VERBS",
    "fallback_reply",
    "looks_like_runtime_fallback",
    "runtime_unready_reason",
]
