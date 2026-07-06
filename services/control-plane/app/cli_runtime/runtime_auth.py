"""Auth error detection and env shaping for CLI runtime dispatch."""

from __future__ import annotations

import os


def looks_like_auth_error(text: str) -> bool:
    lowered = str(text or "").lower()
    return any(
        marker in lowered
        for marker in (
            "invalid api key",
            "incorrect api key",
            "401 unauthorized",
            "authentication required",
            "unauthorized",
        )
    )


def summarize_auth_error(*, family: str, detail: str) -> str:
    trimmed = str(detail or "").strip()
    if family == "cursor":
        if looks_like_auth_error(trimmed):
            return (
                "Cursor rejected CURSOR_API_KEY. Remove or fix the key in /vault, "
                "clear it from the control-plane shell env, or run `cursor agent login` "
                "to use your subscription."
            )
        return trimmed or "Cursor authentication failed."
    if looks_like_auth_error(trimmed):
        return (
            "Codex/OpenAI API key was rejected. Fix keys in /vault or run `codex login`."
        )
    return trimmed or "Codex authentication failed."


def env_without_api_keys(env: dict[str, str], *, family: str) -> dict[str, str]:
    stripped = dict(env)
    if family == "cursor":
        stripped.pop("CURSOR_API_KEY", None)
        return stripped
    stripped.pop("CODEX_API_KEY", None)
    stripped.pop("OPENAI_API_KEY", None)
    return stripped


def env_has_api_key(env: dict[str, str], *, family: str) -> bool:
    if family == "cursor":
        return bool(str(env.get("CURSOR_API_KEY", "")).strip())
    return bool(str(env.get("CODEX_API_KEY", "")).strip() or str(env.get("OPENAI_API_KEY", "")).strip())


def prefer_subscription_over_process_api_key() -> bool:
    return os.environ.get("AXON_WATCH_CURSOR_PREFER_SUBSCRIPTION", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
