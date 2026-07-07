"""Search providers for Axon-X research."""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request

from app.research.policy import research_enabled, validate_url


def _searxng_search(query: str) -> list[dict[str, str]] | None:
    base = str(os.environ.get("AXON_WATCH_SEARXNG_URL", "")).strip().rstrip("/")
    if not base:
        return None
    params = urllib.parse.urlencode({"q": query, "format": "json"})
    url = f"{base}/search?{params}"
    validate_url(url)
    request = urllib.request.Request(url, headers={"User-Agent": "Axon-X-Research/1.0"})
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))
    results = payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(results, list):
        return []
    items: list[dict[str, str]] = []
    for entry in results[:8]:
        if not isinstance(entry, dict):
            continue
        title = str(entry.get("title") or "").strip()
        link = str(entry.get("url") or entry.get("link") or "").strip()
        snippet = str(entry.get("content") or entry.get("snippet") or "").strip()
        if title or link:
            items.append({"title": title or link, "url": link, "snippet": snippet})
    return items


def _duckduckgo_instant_search(query: str) -> list[dict[str, str]]:
    params = urllib.parse.urlencode({"q": query, "format": "json", "no_redirect": "1"})
    url = f"https://api.duckduckgo.com/?{params}"
    validate_url(url)
    request = urllib.request.Request(url, headers={"User-Agent": "Axon-X-Research/1.0"})
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))
    items: list[dict[str, str]] = []
    if not isinstance(payload, dict):
        return items

    abstract = str(payload.get("AbstractText") or "").strip()
    abstract_url = str(payload.get("AbstractURL") or "").strip()
    heading = str(payload.get("Heading") or query).strip()
    if abstract or abstract_url:
        items.append(
            {
                "title": heading or query,
                "url": abstract_url or "https://duckduckgo.com/",
                "snippet": abstract,
            }
        )

    related = payload.get("RelatedTopics")
    if isinstance(related, list):
        for entry in related:
            if not isinstance(entry, dict):
                continue
            if "Topics" in entry:
                continue
            text = str(entry.get("Text") or "").strip()
            link = str(entry.get("FirstURL") or "").strip()
            if text or link:
                items.append({"title": text.split(" - ", 1)[0] if text else link, "url": link, "snippet": text})
            if len(items) >= 8:
                break
    return items[:8]


def search_web(query: str) -> dict[str, object]:
    if not research_enabled():
        raise ValueError("online research is disabled")

    cleaned = query.strip()
    if not cleaned:
        raise ValueError("search query must not be empty")

    provider = "searxng"
    items = _searxng_search(cleaned)
    if items is None:
        provider = "duckduckgo_instant"
        items = _duckduckgo_instant_search(cleaned)

    return {
        "query": cleaned,
        "provider": provider,
        "results": items,
        "count": len(items),
    }
