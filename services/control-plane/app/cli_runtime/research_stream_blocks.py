"""Normalize Cursor + MCP research tool events into :::research transcript blocks."""

from __future__ import annotations

import re
from typing import Any

from app.research.receipts import format_research_block
from app.cli_runtime.stream_blocks.research_items import (
    _normalize_research_query,
    _normalize_tool_name,
    _payload_from_mcp_content,
    _research_meta_from_payload,
    _research_meta_lines,
    _research_query_from_args,
    is_research_mcp_tool_name,
    research_items_from_payload,
    research_items_from_result,
)
from app.cli_runtime.stream_blocks.normalize_transcript import (
    sanitize_research_block_bodies_in_content,
)
from app.cli_runtime.stream_blocks.transcript_dedupe import (
    collapse_duplicated_body,
    dedupe_assistant_paragraphs,
)

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


def normalize_transcript_content(content: str) -> str:
    normalized = collapse_duplicated_body(content)
    normalized = ensure_research_blocks_in_content(normalized)
    normalized = sanitize_research_block_bodies_in_content(normalized)
    normalized = dedupe_research_blocks(normalized)
    normalized = dedupe_assistant_paragraphs(normalized)
    return normalized.strip()