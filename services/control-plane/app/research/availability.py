"""Research availability snapshot for Lane B prompts."""

from __future__ import annotations

import os

from app.research.policy import research_enabled


def research_capability_snapshot() -> dict[str, object]:
    enabled = research_enabled()
    searxng = bool(str(os.environ.get("AXON_WATCH_SEARXNG_URL", "")).strip())
    provider = "searxng" if searxng else ("duckduckgo_instant" if enabled else "none")
    return {
        "available": enabled,
        "provider": provider,
        "tools": ["axon_research_search", "axon_research_fetch"] if enabled else [],
    }


def format_capability_line(snapshot: dict[str, object]) -> str:
    if snapshot.get("available"):
        provider = str(snapshot.get("provider") or "configured")
        return (
            f"Online research: available via audited Axon-X research tools ({provider}). "
            "Use axon_research_search / axon_research_fetch and cite only URLs returned by those tools."
        )
    return (
        "Online research: unavailable in this runtime. Do not claim live web lookups. "
        "Label memory-based answers as prior knowledge, not verified online sources."
    )
