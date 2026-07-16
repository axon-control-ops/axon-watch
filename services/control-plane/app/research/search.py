"""Search providers for Axon-X research."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request


from app.research.policy import research_enabled, validate_url


def _env(*names: str) -> str:
    for name in names:
        value = str(os.environ.get(name, "")).strip()
        if value:
            return value
    return ""


def google_cse_credentials() -> tuple[str, str] | None:
    """Return (api_key, cx) when Google Custom Search is configured.

    Accepts Axon-X names and DashPro-compatible aliases.
    """

    api_key = _env(
        "AXON_WATCH_GOOGLE_CSE_API_KEY",
        "GOOGLE_SEARCH_API_KEY",
        "EXPO_PUBLIC_GOOGLE_CSE_API_KEY",
    )
    cx = _env(
        "AXON_WATCH_GOOGLE_CSE_CX",
        "GOOGLE_CSE_ID",
        "EXPO_PUBLIC_GOOGLE_CSE_CX",
    )
    if api_key and cx:
        return api_key, cx
    return None


def _google_cse_search(query: str) -> list[dict[str, str]] | None:
    creds = google_cse_credentials()
    if creds is None:
        return None
    api_key, cx = creds
    params = urllib.parse.urlencode(
        {
            "key": api_key,
            "cx": cx,
            "q": query,
            "num": "8",
            "safe": "off",
            "hl": "en",
        }
    )
    url = f"https://www.googleapis.com/customsearch/v1?{params}"
    validate_url(url)
    request = urllib.request.Request(url, headers={"User-Agent": "Axon-X-Research/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:240]
        raise ValueError(f"Google CSE error {exc.code}: {body}") from exc

    items_raw = payload.get("items") if isinstance(payload, dict) else None
    if not isinstance(items_raw, list):
        return []
    items: list[dict[str, str]] = []
    for entry in items_raw[:8]:
        if not isinstance(entry, dict):
            continue
        title = str(entry.get("title") or "").strip()
        link = str(entry.get("link") or "").strip()
        snippet = str(entry.get("snippet") or "").strip()
        if title or link:
            items.append({"title": title or link, "url": link, "snippet": snippet})
    return items


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

    provider = "duckduckgo_instant"
    items: list[dict[str, str]] | None = None
    errors: list[str] = []

    if google_cse_credentials() is not None:
        try:
            items = _google_cse_search(cleaned)
            provider = "google_cse"
        except ValueError as exc:
            errors.append(str(exc))
            items = None

    if items is None:
        try:
            items = _searxng_search(cleaned)
            if items is not None:
                provider = "searxng"
        except (ValueError, OSError, urllib.error.URLError) as exc:
            errors.append(f"searxng: {exc}")
            items = None

    if items is None:
        items = _duckduckgo_instant_search(cleaned)
        provider = "duckduckgo_instant"

    payload: dict[str, object] = {
        "query": cleaned,
        "provider": provider,
        "results": items,
        "count": len(items),
    }
    if errors and provider != "google_cse":
        payload["fallback_from"] = errors[0][:240]
    return payload
