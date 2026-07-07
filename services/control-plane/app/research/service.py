"""Orchestration for cached research fetch/search."""

from __future__ import annotations

from app.research.availability import research_capability_snapshot
from app.research.cache import get_cached, set_cached
from app.research.fetch import fetch_url as _fetch_url
from app.research.receipts import append_research_receipt, research_receipt_payload
from app.research.search import search_web as _search_web


def research_status() -> dict[str, object]:
    return research_capability_snapshot()


def fetch_url(url: str, *, run_id: str = "") -> dict[str, object]:
    cached = get_cached("fetch", url)
    if cached is not None:
        return cached

    try:
        payload = _fetch_url(url)
        receipt = research_receipt_payload(
            kind="fetch",
            target=url,
            provider="https_fetch",
            success=True,
            payload={"url": payload.get("url"), "bytes_read": payload.get("bytes_read")},
        )
        append_research_receipt(run_id, receipt)
        result = {"success": True, **payload, "receipt": receipt}
        set_cached("fetch", url, result)
        return result
    except ValueError as exc:
        receipt = research_receipt_payload(
            kind="fetch",
            target=url,
            provider="https_fetch",
            success=False,
            payload={"error": str(exc)},
        )
        append_research_receipt(run_id, receipt)
        return {"success": False, "error": str(exc), "receipt": receipt}


def search_web(query: str, *, run_id: str = "") -> dict[str, object]:
    cached = get_cached("search", query)
    if cached is not None:
        return cached

    try:
        payload = _search_web(query)
        provider = str(payload.get("provider") or "search")
        receipt = research_receipt_payload(
            kind="search",
            target=query,
            provider=provider,
            success=True,
            payload={"count": payload.get("count"), "provider": provider},
        )
        append_research_receipt(run_id, receipt)
        result = {"success": True, **payload, "receipt": receipt}
        set_cached("search", query, result)
        return result
    except ValueError as exc:
        receipt = research_receipt_payload(
            kind="search",
            target=query,
            provider="search",
            success=False,
            payload={"error": str(exc)},
        )
        append_research_receipt(run_id, receipt)
        return {"success": False, "error": str(exc), "receipt": receipt}
