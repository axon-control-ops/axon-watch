"""Sanitize research card bodies that still contain raw MCP envelopes."""

from __future__ import annotations

import re

from app.cli_runtime.stream_blocks.research_items import (
    _looks_like_mcp_content_repr,
    _sanitize_snippet,
)
from app.cli_runtime.stream_blocks.transcript_dedupe import _is_transcript_block_start


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
