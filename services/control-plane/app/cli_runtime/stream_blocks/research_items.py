"""Research result item extraction for stream blocks."""

from __future__ import annotations

import ast
import json
import re
from typing import Any

_RESEARCH_NATIVE_KEYS = (
    "webSearchToolCall",
    "webFetchToolCall",
    "searchToolCall",
    "fetchToolCall",
)

_RESEARCH_MCP_TOOL_NAMES = frozenset(
    {
        "axon_research_search",
        "axon_research_fetch",
        "axon-research-search",
        "axon-research-fetch",
    }
)

_RESEARCH_KEY_HINT = re.compile(
    r"(websearch|webfetch|researchsearch|researchfetch|axonresearch)",
    re.I,
)


def _normalize_tool_name(value: str) -> str:
    return str(value or "").strip().lower().replace("-", "_")


def _normalize_research_query(query: str) -> str:
    return re.sub(r"\s+", " ", str(query or "").strip().lower())


def is_research_mcp_tool_name(name: str) -> bool:
    normalized = _normalize_tool_name(name)
    if normalized in _RESEARCH_MCP_TOOL_NAMES:
        return True
    return normalized.startswith("axon_research_")


def _query_from_args_only(args: dict[str, Any]) -> str:
    nested = args.get("arguments")
    if isinstance(nested, dict):
        for key in ("query", "search_term", "url", "prompt"):
            value = str(nested.get(key) or "").strip()
            if value:
                return value
    for key in ("query", "search_term", "url", "prompt", "searchQuery"):
        value = str(args.get(key) or "").strip()
        if value:
            return value
    return ""


def _research_query_from_args(args: dict[str, Any]) -> str:
    query = _query_from_args_only(args)
    if query:
        return query
    tool_name = str(args.get("tool") or args.get("toolName") or args.get("name") or "").strip()
    if tool_name:
        return tool_name.replace("_", " ")
    return ""


def _tool_name_from_args(args: dict[str, Any]) -> str:
    for key in ("tool", "toolName", "name"):
        value = str(args.get(key) or "").strip()
        if value:
            return value
    return ""


def _parse_json_text(value: str) -> dict[str, Any] | None:
    stripped = value.strip()
    if not stripped.startswith("{"):
        return None
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _payload_from_mcp_content(result: Any) -> dict[str, Any] | None:
    if not isinstance(result, dict):
        return None
    content = result.get("content")
    if isinstance(content, str):
        payload = _unwrap_text_envelope(content)
        if payload is not None:
            return payload
    if isinstance(content, list):
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") != "text":
                continue
            payload = _unwrap_text_envelope(str(block.get("text") or ""))
            if payload is not None:
                return payload
    for key in ("structuredContent", "structured_content"):
        candidate = result.get(key)
        if isinstance(candidate, dict):
            return candidate
    text = str(result.get("text") or "").strip()
    if text:
        return _unwrap_text_envelope(text)
    return None


def _unwrap_text_envelope(value: str) -> dict[str, Any] | None:
    cleaned = value.strip()
    if not cleaned:
        return None

    payload = _parse_json_text(cleaned)
    if payload is not None:
        return payload

    if cleaned.startswith("[{") or cleaned.startswith("{'"):
        try:
            literal = ast.literal_eval(cleaned)
        except (SyntaxError, ValueError):
            literal = None
        if isinstance(literal, list):
            for block in literal:
                if not isinstance(block, dict):
                    continue
                text = block.get("text")
                if isinstance(text, dict):
                    nested = _parse_json_text(str(text.get("text") or ""))
                    if nested is not None:
                        return nested
                if isinstance(text, str):
                    nested = _parse_json_text(text)
                    if nested is not None:
                        return nested

    return None


def _looks_like_mcp_content_repr(value: str) -> bool:
    cleaned = str(value or "").strip()
    if not cleaned:
        return False
    return cleaned.startswith("[{'text'") or cleaned.startswith('[{"text"')


def _snippet_from_partial_envelope(cleaned: str) -> str:
    """Best-effort cleanup when MCP envelope JSON was truncated before parsing."""
    if not cleaned:
        return ""
    query_match = re.search(r'"query"\s*:\s*"([^"]+)"', cleaned)
    if re.search(r'"results"\s*:\s*\[\s*\]', cleaned):
        return str(query_match.group(1) if query_match else "No web results")[:500]
    url_match = re.search(r'"url"\s*:\s*"([^"]+)"', cleaned)
    if url_match and re.search(r'"success"\s*:\s*true', cleaned):
        content_match = re.search(r'"content"\s*:\s*"((?:\\.|[^"\\])*)"', cleaned)
        if content_match:
            try:
                decoded = json.loads(f'"{content_match.group(1)}"')
            except json.JSONDecodeError:
                decoded = content_match.group(1).replace("\\n", "\n")
            return str(decoded).strip()[:500]
        title_match = re.search(r'"title"\s*:\s*"([^"]+)"', cleaned)
        if title_match:
            return title_match.group(1)[:500]
    error_match = re.search(r'"error"\s*:\s*"([^"]+)"', cleaned)
    if error_match:
        return error_match.group(1)[:500]
    return ""


def _sanitize_snippet(snippet: str, *, limit: int = 500) -> str:
    cleaned = str(snippet or "").strip()
    if not cleaned:
        return ""

    if _looks_like_mcp_content_repr(cleaned):
        envelope = _unwrap_text_envelope(cleaned)
        if envelope is not None:
            return _sanitize_snippet(json.dumps(envelope), limit=limit)
        partial = _snippet_from_partial_envelope(cleaned)
        if partial:
            return partial[:limit]

    envelope = _unwrap_text_envelope(cleaned)
    if envelope is not None:
        if envelope.get("success") is False:
            return str(envelope.get("error") or "Research request failed").strip()[:limit]
        content = str(envelope.get("content") or "").strip()
        if content:
            return content[:limit]
        results = envelope.get("results")
        if isinstance(results, list):
            if not results:
                query = str(envelope.get("query") or "").strip()
                return (query or "No web results")[:limit]
            first = results[0]
            if isinstance(first, dict):
                return str(
                    first.get("snippet")
                    or first.get("description")
                    or first.get("title")
                    or ""
                ).strip()[:limit]

    if cleaned.startswith("{") or cleaned.startswith("["):
        payload = _unwrap_text_envelope(cleaned)
        if payload is not None:
            return _sanitize_snippet(json.dumps(payload), limit=limit)

    return cleaned[:limit]


def _research_meta_from_payload(payload: dict[str, Any] | None) -> tuple[str, str]:
    if not payload:
        return "", ""
    provider = str(payload.get("provider") or "").strip()
    content = str(payload.get("content") or "").strip()
    url = str(payload.get("url") or "").strip()
    if url or content:
        return provider, "fetch"
    if any(payload.get(key) is not None for key in ("results", "items", "query")):
        return provider, "search"
    return provider, ""


def _research_meta_lines(*, provider: str = "", kind: str = "") -> list[str]:
    lines: list[str] = []
    if kind.strip():
        lines.append(f"@kind {kind.strip()}")
    if provider.strip():
        lines.append(f"@provider {provider.strip()}")
    return lines


def research_items_from_payload(payload: dict[str, Any], *, limit: int = 8) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []

    if payload.get("success") is False:
        error = str(payload.get("error") or "Research request failed").strip()
        url = str(payload.get("url") or "").strip()
        return [
            {
                "title": "Fetch failed",
                "url": url,
                "snippet": error,
            }
        ]

    raw_results: Any = None
    for key in ("results", "items", "sources", "citations", "matches"):
        candidate = payload.get(key)
        if isinstance(candidate, list):
            raw_results = candidate
            break

    if isinstance(raw_results, list):
        if not raw_results:
            query = str(payload.get("query") or "").strip()
            if query:
                provider = str(payload.get("provider") or "").strip()
                snippet = query if not provider else f"{query} · {provider}"
                return [{"title": "No web results", "url": "", "snippet": snippet}]
        for entry in raw_results:
            if not isinstance(entry, dict):
                continue
            title = str(entry.get("title") or entry.get("name") or entry.get("label") or "").strip()
            url = str(entry.get("url") or entry.get("link") or entry.get("href") or "").strip()
            snippet = _sanitize_snippet(
                str(
                    entry.get("snippet")
                    or entry.get("summary")
                    or entry.get("description")
                    or entry.get("content")
                    or ""
                )
            )
            if not title and not url and not snippet:
                continue
            items.append(
                {
                    "title": title or (url or "Source"),
                    "url": url,
                    "snippet": snippet,
                }
            )
            if len(items) >= limit:
                return items

    url = str(payload.get("url") or "").strip()
    content = str(payload.get("content") or "").strip()
    if _looks_like_mcp_content_repr(content):
        content = ""
    if url or content:
        title = str(payload.get("title") or payload.get("hostname") or url or "Fetched page").strip()
        snippet = _sanitize_snippet(content, limit=2400)
        items.append({"title": title, "url": url, "snippet": snippet})

    return items[:limit]


def research_items_from_result(result: Any, *, limit: int = 8) -> list[dict[str, str]]:
    if not isinstance(result, dict):
        return []

    mcp_payload = _payload_from_mcp_content(result)
    if mcp_payload is not None:
        return research_items_from_payload(mcp_payload, limit=limit)

    containers: list[dict[str, Any]] = []
    success = result.get("success")
    if isinstance(success, dict):
        containers.append(success)
    containers.append(result)

    for container in containers:
        items = research_items_from_payload(container, limit=limit)
        if items:
            return items
    return []