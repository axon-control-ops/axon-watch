"""Truthful fallback copy for unavailable versus crashed CLI runtimes."""

from __future__ import annotations


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
    if failure_phase == "run_error":
        label = (runtime_label or "the selected CLI runtime").strip()
        return (
            f"Lane B ({composer_mode}) failed on {label}: {reason}. "
            "Open Runtime or `/vault` if auth looks wrong, then retry."
        )
    return (
        f"Lane B ({composer_mode}) cannot start because no CLI runtime is ready: {reason}. "
        "Open Runtime or `/vault`, then retry."
    )


__all__ = ["fallback_reply", "runtime_unready_reason"]
