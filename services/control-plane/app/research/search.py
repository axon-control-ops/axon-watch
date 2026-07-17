"""Search providers for Axon-X research."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from urllib.parse import urlparse


from app.research.env_file import load_repo_env_file
from app.research.policy import research_enabled, validate_url


def _env(*names: str) -> str:
    for name in names:
        value = str(os.environ.get(name, "")).strip()
        if value:
            return value
    return ""


_GOOGLE_CSE_API_KEY_NAMES = (
    "AXON_WATCH_GOOGLE_CSE_API_KEY",
    "GOOGLE_SEARCH_API_KEY",
    "EXPO_PUBLIC_GOOGLE_CSE_API_KEY",
    "google_cse_api_key",
)
_GOOGLE_CSE_CX_NAMES = (
    "AXON_WATCH_GOOGLE_CSE_CX",
    "GOOGLE_CSE_ID",
    "EXPO_PUBLIC_GOOGLE_CSE_CX",
    "google_cse_cx",
)


def _first_env_value(names: tuple[str, ...], env: dict[str, str]) -> str:
    for name in names:
        value = str(env.get(name, "")).strip()
        if value:
            return value
    return ""


def _vault_env() -> dict[str, str]:
    try:
        from app.cli_runtime.vault_keys import runtime_vault_env

        return runtime_vault_env()
    except Exception:
        return {}


def google_cse_credentials() -> tuple[str, str] | None:
    """Return (api_key, cx) when Google Custom Search is configured.

    Accepts Axon-X names, DashPro-compatible aliases, unlocked /vault secrets,
    and repo-root .env gaps.
    """

    def _pair(env: dict[str, str]) -> tuple[str, str] | None:
        api_key = _first_env_value(_GOOGLE_CSE_API_KEY_NAMES, env)
        cx = _first_env_value(_GOOGLE_CSE_CX_NAMES, env)
        if api_key and cx:
            return api_key, cx
        return None

    process_env = {key: str(value) for key, value in os.environ.items() if str(value or "").strip()}
    found = _pair(process_env)
    if found is not None:
        return found

    found = _pair(_vault_env())
    if found is not None:
        return found

    # Cursor MCP often starts with a minimal env; fill gaps from local .env.
    load_repo_env_file()
    return _pair({key: str(value) for key, value in os.environ.items() if str(value or "").strip()})


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
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Axon-X-Research/1.0",
            "Accept": "application/json",
        },
    )
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


def searxng_base_url() -> str:
    """Resolve SearXNG base URL from process env, vault, then repo .env."""

    def _from_env(env: dict[str, str]) -> str:
        return str(env.get("AXON_WATCH_SEARXNG_URL", "")).strip().rstrip("/")

    process_env = {key: str(value) for key, value in os.environ.items() if str(value or "").strip()}
    found = _from_env(process_env)
    if found:
        return found

    found = _from_env(_vault_env())
    if found:
        return found

    load_repo_env_file()
    return _from_env({key: str(value) for key, value in os.environ.items() if str(value or "").strip()})


def _validate_searxng_request(url: str, base: str) -> None:
    """Allow loopback only for the operator-configured SearXNG base URL."""
    if not research_enabled():
        raise ValueError("online research is disabled")
    parsed = urlparse(url.strip())
    base_parsed = urlparse(base.strip().rstrip("/"))
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("only http(s) URLs are allowed")
    if not parsed.hostname or not base_parsed.hostname:
        raise ValueError("URL hostname is required")
    if parsed.netloc != base_parsed.netloc:
        raise ValueError("searxng request must target configured AXON_WATCH_SEARXNG_URL")


def _searxng_search(query: str) -> list[dict[str, str]] | None:
    base = searxng_base_url()
    if not base:
        return None
    params = urllib.parse.urlencode({"q": query, "format": "json"})
    url = f"{base}/search?{params}"
    _validate_searxng_request(url, base)
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Axon-X-Research/1.0",
            "Accept": "application/json",
        },
    )
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
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Axon-X-Research/1.0",
            "Accept": "application/json",
        },
    )
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

    if searxng_base_url():
        try:
            items = _searxng_search(cleaned)
            if items is not None:
                provider = "searxng"
        except (ValueError, OSError, urllib.error.URLError) as exc:
            errors.append(f"searxng: {exc}")
            items = None

    if items is None and google_cse_credentials() is not None:
        try:
            items = _google_cse_search(cleaned)
            provider = "google_cse"
        except ValueError as exc:
            errors.append(str(exc))
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
