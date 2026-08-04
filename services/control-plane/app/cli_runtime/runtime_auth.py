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
            "authentication_failed",
            "authentication failed",
            "oauth access token has been revoked",
            "unauthorized",
        )
    )


def summarize_auth_error(*, family: str, detail: str, had_api_key: bool = False) -> str:
    trimmed = str(detail or "").strip()
    if family == "cursor":
        if looks_like_auth_error(trimmed):
            if had_api_key:
                return (
                    "Cursor rejected CURSOR_API_KEY. Remove or fix the key in /vault, "
                    "clear it from the control-plane shell env, or run `cursor agent login` "
                    "to use your subscription."
                )
            return (
                "Cursor authentication failed. Run `cursor agent login` on the host "
                "or fix runtime auth in /vault."
            )
        return trimmed or "Cursor authentication failed."
    if family == "claude":
        if looks_like_auth_error(trimmed):
            if had_api_key:
                return (
                    "Claude rejected ANTHROPIC_API_KEY. Fix the key in /vault, "
                    "clear it from the control-plane shell env, or run `claude auth login` "
                    "to use your Claude subscription."
                )
            return (
                "Claude authentication failed. Run `claude auth login` on the host "
                "or fix runtime auth in /vault."
            )
        return trimmed or "Claude authentication failed."
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
    if family == "claude":
        stripped.pop("ANTHROPIC_API_KEY", None)
        return stripped
    stripped.pop("CODEX_API_KEY", None)
    stripped.pop("OPENAI_API_KEY", None)
    return stripped


def env_has_api_key(env: dict[str, str], *, family: str) -> bool:
    if family == "cursor":
        return bool(str(env.get("CURSOR_API_KEY", "")).strip())
    if family == "claude":
        return bool(str(env.get("ANTHROPIC_API_KEY", "")).strip())
    return bool(str(env.get("CODEX_API_KEY", "")).strip() or str(env.get("OPENAI_API_KEY", "")).strip())


def prefer_subscription_over_process_api_key() -> bool:
    return os.environ.get("AXON_WATCH_CURSOR_PREFER_SUBSCRIPTION", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def cursor_subscription_ready(auth: dict[str, object] | None) -> bool:
    """True when Cursor CLI subscription auth should win over a vault/shell API key."""
    record = auth or {}
    auth_method = str(record.get("auth_method") or "")
    if auth_method == "oauth":
        return True
    message = str(record.get("message") or "").lower()
    provider = str(record.get("provider_label") or "").lower()
    return "subscription" in message or "subscription" in provider


def claude_subscription_ready(auth: dict[str, object] | None) -> bool:
    """True when Claude Code subscription auth should win over ANTHROPIC_API_KEY."""
    record = auth or {}
    auth_method = str(record.get("auth_method") or "")
    if auth_method in {"oauth", "claude.ai"}:
        return True
    message = str(record.get("message") or "").lower()
    provider = str(record.get("provider_label") or "").lower()
    return "subscription" in message or provider == "claude"


def codex_subscription_ready(auth: dict[str, object] | None) -> bool:
    """True when a cached ChatGPT session should beat a Codex API-key overlay."""
    record = auth or {}
    auth_method = str(record.get("auth_method") or "")
    if auth_method in {"chatgpt", "oauth"}:
        return True
    message = str(record.get("message") or "").lower()
    provider = str(record.get("provider_label") or "").lower()
    return "chatgpt" in message or provider == "codex"


def cursor_dispatch_env(
    env: dict[str, str],
    *,
    auth: dict[str, object] | None = None,
) -> dict[str, str]:
    """Shape subprocess env for Cursor CLI dispatch (subscription beats stale API keys)."""
    if not str(env.get("CURSOR_API_KEY", "")).strip():
        return env
    if cursor_subscription_ready(auth) or prefer_subscription_over_process_api_key():
        return env_without_api_keys(env, family="cursor")
    return env


def claude_dispatch_env(
    env: dict[str, str],
    *,
    auth: dict[str, object] | None = None,
) -> dict[str, str]:
    """Shape subprocess env for Claude Code (subscription beats stale API keys)."""
    if not str(env.get("ANTHROPIC_API_KEY", "")).strip():
        return env
    if claude_subscription_ready(auth) or prefer_subscription_over_process_api_key():
        return env_without_api_keys(env, family="claude")
    return env


def codex_dispatch_env(
    env: dict[str, str],
    *,
    auth: dict[str, object] | None = None,
) -> dict[str, str]:
    """Shape Codex execution env so a valid ChatGPT login wins over a stale key."""
    if not env_has_api_key(env, family="codex"):
        return env
    if codex_subscription_ready(auth):
        return env_without_api_keys(env, family="codex")
    return env
