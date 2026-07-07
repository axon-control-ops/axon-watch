"""Normalize Cursor + MCP research tool events into :::research transcript blocks."""

from __future__ import annotations

import ast
import json
import re
from typing import Any

from app.research.receipts import format_research_block

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


def is_research_mcp_tool_name(name: str) -> bool:
    normalized = _normalize_tool_name(name)
    if normalized in _RESEARCH_MCP_TOOL_NAMES:
        return True
    return normalized.startswith("axon_research_")


def _normalize_research_query(query: str) -> str:
    return re.sub(r"\s+", " ", str(query or "").strip().lower())


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


def research_display_query(tool_call: dict[str, Any]) -> str:
    matched = _call_from_tool_call(tool_call)
    if matched is None:
        return ""
    _key, args, _call = matched
    query = _query_from_args_only(args)
    if query:
        return query
    tool_name = _normalize_tool_name(_tool_name_from_args(args) or _key.replace("ToolCall", ""))
    if tool_name == "axon_research_search":
        return "Web search"
    if tool_name == "axon_research_fetch":
        return "Page fetch"
    return _research_query_from_args(args) or "Research"


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


def _call_from_tool_call(tool_call: dict[str, Any]) -> tuple[str, dict[str, Any], dict[str, Any]] | None:
    for key, call in tool_call.items():
        if not isinstance(call, dict):
            continue
        args = call.get("args") if isinstance(call.get("args"), dict) else {}

        if key in _RESEARCH_NATIVE_KEYS or _RESEARCH_KEY_HINT.search(key):
            query = _research_query_from_args(args) or key.replace("ToolCall", "")
            return key, args, call

        if key == "mcpToolCall" or key.endswith("McpToolCall"):
            tool_name = _tool_name_from_args(args)
            if is_research_mcp_tool_name(tool_name):
                query = _research_query_from_args(args) or tool_name.replace("_", " ")
                return key, args, call

        if key.endswith("ToolCall"):
            tool_name = _tool_name_from_args(args) or key[: -len("ToolCall")]
            if is_research_mcp_tool_name(tool_name) or _RESEARCH_KEY_HINT.search(tool_name):
                query = _research_query_from_args(args) or tool_name.replace("_", " ")
                return key, args, call

    return None


def research_query_from_tool_call(tool_call: dict[str, Any]) -> str:
    return research_display_query(tool_call)


def research_started_block(query: str) -> str:
    trimmed = query.strip() or "Research"
    return f"\n:::research {trimmed}\n"


def research_completed_block(
    query: str,
    items: list[dict[str, str]],
    *,
    open_query: str | None = None,
    provider: str = "",
    kind: str = "",
) -> str:
    trimmed = query.strip() or "Research"
    if open_query is not None:
        lines = _research_meta_lines(provider=provider, kind=kind)
        for item in items:
            title = str(item.get("title") or "Source").strip()
            url = str(item.get("url") or "").strip()
            snippet = str(item.get("snippet") or "").strip()
            lines.append(f"- {title} | {url or 'about:blank'}")
            if snippet:
                lines.append(snippet)
        lines.append(":::\n")
        body = "\n".join(lines)
        return f"\n{body}" if body.strip() else "\n:::\n"
    return format_research_block(trimmed, items, provider=provider, kind=kind)


def research_block_from_tool_call(
    tool_call: dict[str, Any],
    *,
    open_query: str | None = None,
) -> str:
    matched = _call_from_tool_call(tool_call)
    if matched is None:
        return ""
    key, args, call = matched
    query = research_display_query(tool_call)
    result = call.get("result")
    payload = _payload_from_mcp_content(result) if isinstance(result, dict) else None
    provider, kind = _research_meta_from_payload(payload)
    tool_name = _normalize_tool_name(_tool_name_from_args(args) or key.replace("ToolCall", ""))
    if not kind:
        if "fetch" in tool_name:
            kind = "fetch"
        elif "search" in tool_name:
            kind = "search"
    items = research_items_from_result(result)
    if not query and not items:
        return ""
    return research_completed_block(
        query,
        items,
        open_query=open_query,
        provider=provider,
        kind=kind,
    )


def research_started_block_from_event(event: dict[str, Any]) -> str:
    if event.get("type") != "tool_call" or event.get("subtype") != "started":
        return ""
    tool_call = event.get("tool_call")
    if not isinstance(tool_call, dict):
        return ""
    matched = _call_from_tool_call(tool_call)
    if matched is None:
        return ""
    _key, args, _call = matched
    # Cursor often omits arguments on started events; wait for completed to avoid
    # duplicate headers like "axon research search" followed by the real query.
    query = _query_from_args_only(args)
    if not query:
        return ""
    return research_started_block(query)


def research_completed_block_from_event(
    event: dict[str, Any],
    *,
    open_query: str | None = None,
) -> str:
    if event.get("type") != "tool_call" or event.get("subtype") != "completed":
        return ""
    tool_call = event.get("tool_call")
    if not isinstance(tool_call, dict):
        return ""
    return research_block_from_tool_call(tool_call, open_query=open_query)


def ensure_research_blocks_in_content(content: str) -> str:
    """Upgrade generic :::tool research lines to :::research when possible."""
    if ":::research" in content or ":::tool" not in content:
        return content

    lines = content.split("\n")
    out: list[str] = []
    for line in lines:
        match = re.match(r"^:::tool\s+(.+)$", line.strip())
        if not match:
            out.append(line)
            continue
        label = match.group(1).strip().lower()
        if not (
            "axon research" in label
            or "research search" in label
            or "research fetch" in label
            or label.startswith("axon_research")
        ):
            out.append(line)
            continue
        query = label.replace("axon research", "").replace("search", "").replace("fetch", "").strip()
        out.append(f":::research {query or 'Research'}")
        out.append(":::")
    return "\n".join(out)


def dedupe_research_blocks(content: str) -> str:
    """Collapse duplicate :::research headers and empty open blocks."""
    if ":::research" not in content:
        return content

    lines = content.split("\n")
    filtered: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if re.match(r"^:::research\s+", line.strip()):
            probe = index + 1
            while probe < len(lines) and not lines[probe].strip():
                probe += 1
            if probe < len(lines) and re.match(r"^:::research\s+", lines[probe].strip()):
                index += 1
                continue
        filtered.append(line)
        index += 1

    out: list[str] = []
    index = 0
    while index < len(filtered):
        match = re.match(r"^:::research\s+(.+)$", filtered[index].strip())
        if not match:
            out.append(filtered[index])
            index += 1
            continue

        query = match.group(1).strip()
        normalized = _normalize_research_query(query)
        index += 1

        while index < len(filtered):
            next_match = re.match(r"^:::research\s+(.+)$", filtered[index].strip())
            if next_match and _normalize_research_query(next_match.group(1)) == normalized:
                index += 1
                continue
            break

        out.append(f":::research {query}")
        body: list[str] = []
        while index < len(filtered):
            if filtered[index].strip() == ":::":
                index += 1
                break
            next_header = re.match(r"^:::research\s+(.+)$", filtered[index].strip())
            if next_header:
                break
            body.append(filtered[index])
            index += 1
        out.extend(body)
        if body or out[-1].startswith(":::research"):
            out.append(":::")

    return "\n".join(out)


def _dedupe_plain_paragraphs(content: str) -> str:
    paragraphs = [chunk.strip() for chunk in re.split(r"\n{2,}", content.strip()) if chunk.strip()]
    deduped: list[str] = []
    for paragraph in paragraphs:
        if deduped and deduped[-1] == paragraph:
            continue
        deduped.append(paragraph)
    return "\n\n".join(deduped)


_EDIT_HEADER_RE = re.compile(r"^:::edit\s+.+?\s+\+\d+\s+-\d+\s*$")
_TOOL_HEADER_RE = re.compile(r"^:::tool\s+.+$")
_RESEARCH_HEADER_RE = re.compile(r"^:::research\s+.+$")
_TERMINAL_HEADER_RE = re.compile(r"^:::terminal\s+.+$")
_BLOCK_START_RE = re.compile(r"^:::(thinking|edit|terminal|tool|research)\b", re.MULTILINE)


def _is_transcript_block_start(line: str) -> bool:
    stripped = line.strip()
    if stripped == ":::thinking":
        return True
    return bool(
        _EDIT_HEADER_RE.match(stripped)
        or _TOOL_HEADER_RE.match(stripped)
        or _RESEARCH_HEADER_RE.match(stripped)
        or _TERMINAL_HEADER_RE.match(stripped)
    )


def _advance_past_transcript_block(lines: list[str], start: int) -> int:
    line = lines[start]
    stripped = line.strip()
    if _TOOL_HEADER_RE.match(stripped):
        return start + 1

    index = start + 1
    while index < len(lines):
        if lines[index].strip() == ":::":
            return index + 1
        index += 1
    return len(lines)


def _dedupe_prose_segment(content: str) -> str:
    """Collapse duplicate lines/paragraphs inside a prose-only transcript gap."""
    if not content.strip():
        return content

    leading = len(content) - len(content.lstrip("\n"))
    trailing = len(content) - len(content.rstrip("\n"))
    body = content.strip("\n")
    if not body:
        return content

    deduped_lines: list[str] = []
    for line in body.split("\n"):
        if line.strip() and deduped_lines and deduped_lines[-1].strip() == line.strip():
            continue
        if not line.strip() and deduped_lines and not deduped_lines[-1].strip():
            continue
        deduped_lines.append(line)

    body = _dedupe_plain_paragraphs("\n".join(deduped_lines))
    return ("\n" * leading) + body + ("\n" * trailing)


def _dedupe_block_structured_paragraphs(content: str) -> str:
    lines = content.split("\n")
    chunks: list[str] = []
    prose_buf: list[str] = []
    index = 0

    def flush_prose() -> None:
        nonlocal prose_buf
        if not prose_buf:
            return
        chunks.append(_dedupe_prose_segment("\n".join(prose_buf)))
        prose_buf = []

    while index < len(lines):
        line = lines[index]
        if _is_transcript_block_start(line):
            flush_prose()
            end = _advance_past_transcript_block(lines, index)
            chunks.append("\n".join(lines[index:end]))
            index = end
            continue
        prose_buf.append(line)
        index += 1

    flush_prose()
    return "\n".join(chunks)


def dedupe_assistant_paragraphs(content: str) -> str:
    """Collapse exact duplicate paragraphs in plain assistant prose only."""
    if not content.strip():
        return content
    if _BLOCK_START_RE.search(content):
        return _dedupe_block_structured_paragraphs(content)

    marker_index = content.rfind("\n:::\n")
    if marker_index >= 0:
        prefix = content[: marker_index + len("\n:::\n")]
        suffix = content[marker_index + len("\n:::\n") :]
        deduped_suffix = _dedupe_plain_paragraphs(suffix)
        return f"{prefix}{deduped_suffix}" if deduped_suffix else prefix.rstrip()

    return _dedupe_plain_paragraphs(content)


def sanitize_research_block_bodies_in_content(content: str) -> str:
    """Rewrite research card snippets that still contain raw MCP envelopes."""
    if ":::research" not in content:
        return content

    lines = content.split("\n")
    out: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if not re.match(r"^:::research\s+", line.strip()):
            out.append(line)
            index += 1
            continue

        out.append(line)
        index += 1
        while index < len(lines):
            current = lines[index]
            if current.strip() == ":::":
                out.append(current)
                index += 1
                break
            if re.match(r"^:::research\s+", current.strip()):
                break

            stripped = current.strip()
            if stripped.startswith("- ") and " | " in stripped:
                out.append(current)
                index += 1
                snippet_lines: list[str] = []
                while index < len(lines):
                    peek = lines[index]
                    if (
                        peek.strip() == ":::"
                        or re.match(r"^:::research\s+", peek.strip())
                        or _is_transcript_block_start(peek)
                    ):
                        break
                    if peek.strip().startswith("- ") and " | " in peek.strip():
                        break
                    snippet_lines.append(peek)
                    index += 1
                raw_snippet = "\n".join(snippet_lines).strip()
                cleaned = _sanitize_snippet(raw_snippet)
                if cleaned:
                    out.append(cleaned)
                continue

            if _looks_like_mcp_content_repr(stripped) or (
                stripped.startswith("{") and '"success"' in stripped
            ):
                cleaned = _sanitize_snippet(stripped)
                if cleaned:
                    out.append(cleaned)
                index += 1
                continue

            out.append(current)
            index += 1

    return "\n".join(out)


def normalize_transcript_content(content: str) -> str:
    normalized = ensure_research_blocks_in_content(content)
    normalized = sanitize_research_block_bodies_in_content(normalized)
    normalized = dedupe_research_blocks(normalized)
    normalized = dedupe_assistant_paragraphs(normalized)
    return normalized.strip()
