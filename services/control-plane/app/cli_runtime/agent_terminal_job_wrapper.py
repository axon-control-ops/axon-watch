#!/usr/bin/env python3
"""Immutable in-sandbox client for Axon-owned terminal jobs.

This is intentionally materialized from the running control-plane package,
not resolved through PATH. A PATH shim may be a workspace symlink and is not a
valid trust anchor for an agent sandbox.
"""

from __future__ import annotations

import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


def _usage() -> int:
    print(
        "usage: axon-agent-terminal-job [--workspace ID] [--no-stream] [--run-id ID]\n"
        "                               [--target workspace|sandbox] -- <command...>\n"
        "       axon-agent-terminal-job --status JOB_ID --workspace ID",
        file=sys.stderr,
    )
    return 2


def _request(url: str, *, payload: dict[str, object] | None = None) -> dict[str, object]:
    headers = {"Accept": "application/json"}
    token = os.environ.get("AXON_WATCH_OPERATOR_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(url, data=data, headers=headers, method="POST" if data else "GET")
    try:
        with urlopen(request, timeout=20) as response:  # nosec B310 — local control-plane URL is configured by operator
            raw = response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"terminal job request failed ({exc.code}): {raw}") from exc
    except URLError as exc:
        raise RuntimeError(f"terminal job request failed: {exc.reason}") from exc
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"terminal job returned invalid JSON: {raw}") from exc
    if not isinstance(decoded, dict):
        raise RuntimeError("terminal job returned an invalid response")
    return decoded


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    workspace_id = os.environ.get("AXON_WATCH_WORKSPACE_ID", "").strip()
    source_workspace_id = os.environ.get("AXON_AGENT_SOURCE_WORKSPACE_ID", workspace_id).strip()
    run_id = os.environ.get("AXON_WATCH_RUN_ID", "").strip()
    stream_to_chat = True
    status_job_id = ""
    target = ""
    command: list[str] = []
    while arguments:
        item = arguments.pop(0)
        if item == "--workspace" and arguments:
            workspace_id = arguments.pop(0).strip()
        elif item == "--run-id" and arguments:
            run_id = arguments.pop(0).strip()
        elif item == "--status" and arguments:
            status_job_id = arguments.pop(0).strip()
        elif item == "--target" and arguments:
            target = arguments.pop(0).strip().lower()
        elif item == "--no-stream":
            stream_to_chat = False
        elif item in {"-h", "--help"}:
            return _usage()
        elif item == "--":
            command = arguments
            break
        else:
            command = [item, *arguments]
            break
    if not workspace_id:
        print("workspace_id required (pass --workspace or set AXON_WATCH_WORKSPACE_ID)", file=sys.stderr)
        return 1
    base = os.environ.get("AXON_WATCH_CONTROL_PLANE_URL", "http://127.0.0.1:8787").rstrip("/")
    endpoint = f"{base}/api/workspaces/{quote(workspace_id, safe='')}/terminal/agent-jobs"
    try:
        if status_job_id:
            response = _request(f"{endpoint}/{quote(status_job_id, safe='')}")
            print(json.dumps(response, indent=2, sort_keys=True))
            return 0
        if not command:
            return _usage()
        payload: dict[str, object] = {"command": " ".join(command), "stream_to_chat": stream_to_chat}
        if run_id:
            payload["run_id"] = run_id
        if source_workspace_id:
            payload["source_workspace_id"] = source_workspace_id
        if target:
            payload["target"] = target
        response = _request(endpoint, payload=payload)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    job_id = str(response.get("job_id") or "")
    if not job_id:
        print(f"enqueue failed: {json.dumps(response, sort_keys=True)}", file=sys.stderr)
        return 1
    print(f"job_id={job_id}")
    print(f"status={response.get('status') or '?'}")
    print(f"session_id={response.get('session_id') or '?'}")
    print(f"target={response.get('target') or 'workspace'}")
    print(f"cwd={response.get('cwd') or '?'}")
    print(f"stream_to_chat={str(bool(response.get('stream_to_chat'))).lower()}")
    receipt = str(response.get("receipt") or "").strip()
    if receipt:
        print(receipt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
