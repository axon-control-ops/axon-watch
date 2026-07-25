"""Research availability snapshot for Lane B prompts."""

from __future__ import annotations

from app.research.policy import research_enabled
from app.research.search import google_cse_credentials, searxng_base_url


def research_capability_snapshot() -> dict[str, object]:
    enabled = research_enabled()
    if not enabled:
        provider = "none"
    elif searxng_base_url():
        provider = "searxng"
    elif google_cse_credentials() is not None:
        provider = "google_cse"
    else:
        provider = "duckduckgo_instant"
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
            "Before citing any live web fact, call axon_research_search or axon_research_fetch. "
            "Do not use built-in webSearch/webFetch tools — they are unavailable in this headless runtime. "
            "Cite only URLs returned by the audited tools."
        )
    return (
        "Online research: unavailable in this runtime. Do not claim live web lookups. "
        "Label memory-based answers as prior knowledge, not verified online sources."
    )
