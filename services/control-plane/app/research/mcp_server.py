"""Stdio MCP server exposing audited Axon-X research tools."""

from __future__ import annotations

import json
import sys

from app.research.env_file import load_repo_env_file
from app.research.service import fetch_url, search_web

load_repo_env_file()


def _send(payload: dict[str, object]) -> None:
    sys.stdout.write(json.dumps(payload) + "\n")
    sys.stdout.flush()


def _tool_result_text(payload: dict[str, object]) -> dict[str, object]:
    return {"content": [{"type": "text", "text": json.dumps(payload, indent=2)}]}


def _handle_initialize(request_id: object) -> None:
    _send(
        {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "axon-research", "version": "1.0.0"},
            },
        }
    )


def _handle_tools_list(request_id: object) -> None:
    _send(
        {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": [
                    {
                        "name": "axon_research_search",
                        "description": "Search the public web through Axon-X audited research.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {"query": {"type": "string"}},
                            "required": ["query"],
                        },
                    },
                    {
                        "name": "axon_research_fetch",
                        "description": "Fetch readable text from an https URL through Axon-X audited research.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {"url": {"type": "string"}},
                            "required": ["url"],
                        },
                    },
                ]
            },
        }
    )


def _handle_tools_call(request_id: object, params: dict[str, object]) -> None:
    name = str(params.get("name") or "")
    arguments = params.get("arguments") if isinstance(params.get("arguments"), dict) else {}
    if name == "axon_research_search":
        result = search_web(str(arguments.get("query") or ""))
    elif name == "axon_research_fetch":
        result = fetch_url(str(arguments.get("url") or ""))
    else:
        _send(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": f"unknown tool: {name}"},
            }
        )
        return
    _send({"jsonrpc": "2.0", "id": request_id, "result": _tool_result_text(result)})


def main() -> None:
    for line in sys.stdin:
        stripped = line.strip()
        if not stripped:
            continue
        try:
            message = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if not isinstance(message, dict):
            continue
        method = str(message.get("method") or "")
        request_id = message.get("id")
        params = message.get("params") if isinstance(message.get("params"), dict) else {}
        if method == "initialize":
            _handle_initialize(request_id)
        elif method == "notifications/initialized":
            continue
        elif method == "tools/list":
            _handle_tools_list(request_id)
        elif method == "tools/call":
            _handle_tools_call(request_id, params)
        elif request_id is not None:
            _send(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32601, "message": f"unsupported method: {method}"},
                }
            )


if __name__ == "__main__":
    main()
