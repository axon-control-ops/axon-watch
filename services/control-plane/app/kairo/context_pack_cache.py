"""Short-lived context-pack cache so follow-ups reuse fresh DTOs (OP-C5 / M5)."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

_PACK_TTL_SECONDS = 10.0
_PACK_CACHE: dict[str, tuple[dict[str, Any], float]] = {}


def _cache_key(workspace_id: str | None) -> str:
    scoped = workspace_id.strip() if workspace_id else ""
    return scoped or "__global__"


def get_cached_context_pack(
    workspace_id: str | None,
    builder: Callable[[], dict[str, Any]],
    *,
    now: Callable[[], float] | None = None,
    ttl_seconds: float = _PACK_TTL_SECONDS,
) -> dict[str, Any]:
    """Return a cached pack when still within TTL; otherwise rebuild and store."""
    clock = now or time.monotonic
    key = _cache_key(workspace_id)
    cached = _PACK_CACHE.get(key)
    if cached is not None:
        pack, stored_at = cached
        if clock() - stored_at < ttl_seconds:
            return pack
    pack = builder()
    _PACK_CACHE[key] = (pack, clock())
    return pack


def clear_pack_cache_for_tests() -> None:
    _PACK_CACHE.clear()


__all__ = [
    "clear_pack_cache_for_tests",
    "get_cached_context_pack",
]
