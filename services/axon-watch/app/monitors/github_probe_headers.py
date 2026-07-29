"""Shared GitHub API probe header helpers for monitors and connectors."""

from __future__ import annotations

from urllib.parse import urlsplit


_GITHUB_TOKEN_ENV_KEYS = (
    "GITHUB_TOKEN",
    "GH_TOKEN",
    "AXON_GITHUB_TOKEN",
)

_GITHUB_TOKEN_PREFIXES = (
    "ghp_",
    "gho_",
    "ghu_",
    "ghs_",
    "ghr_",
    "github_pat_",
)


def is_github_api_url(url: str) -> bool:
    host = (urlsplit(str(url or "").strip()).hostname or "").lower()
    return host == "api.github.com" or host.endswith(".api.github.com")


def _looks_like_placeholder_token(token: str) -> bool:
    text = str(token or "").strip()
    if not text:
        return True
    lowered = text.lower()
    if text.startswith("__") and text.endswith("__"):
        return True
    if text.startswith("<") and text.endswith(">"):
        return True
    if "${" in text or text.startswith("$"):
        return True
    exact = {
        "replace",
        "changeme",
        "change-me",
        "your_token",
        "your-token",
        "yourtoken",
        "example",
        "placeholder",
        "todo",
        "xxx",
        "null",
        "none",
        "n/a",
    }
    if lowered in exact:
        return True
    # Common dotenv templates like REPLACE_ME / CHANGE_ME without wrapping.
    return lowered in {"replace_me", "insert_token", "add_token_here"}


def looks_like_github_token(token: str) -> bool:
    text = str(token or "").strip()
    if not text or _looks_like_placeholder_token(text):
        return False
    return any(text.startswith(prefix) for prefix in _GITHUB_TOKEN_PREFIXES)


def resolve_github_token(env: dict[str, str] | None = None) -> str:
    """Pick a usable GitHub token, skipping dotenv placeholders that would 401."""
    source = env if env is not None else {}
    fallback = ""
    for key in _GITHUB_TOKEN_ENV_KEYS:
        token = str(source.get(key) or "").strip()
        if not token or _looks_like_placeholder_token(token):
            continue
        if looks_like_github_token(token):
            return token
        if not fallback:
            fallback = token
    return fallback


def github_api_headers(env: dict[str, str] | None = None) -> dict[str, str]:
    """Headers that keep GitHub health probes off the tiny unauthenticated quota."""
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "Axon-Watch-Monitor/1.0",
    }
    token = resolve_github_token(env)
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def looks_like_github_rate_limit(*, status_code: int, body: str = "", headers: object = None) -> bool:
    if int(status_code) not in {403, 429}:
        return False
    text = str(body or "").lower()
    if "rate limit" in text or "rate_limit" in text:
        return True
    if headers is None:
        return False
    remaining = ""
    try:
        remaining = str(headers.get("X-RateLimit-Remaining") or headers.get("x-ratelimit-remaining") or "")
    except Exception:
        remaining = ""
    return remaining.strip() == "0"
