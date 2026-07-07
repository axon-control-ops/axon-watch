"""WebSocket terminal session handler for workspace-scoped PTY attachment."""

from __future__ import annotations

import asyncio
import contextlib
import json
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from app.terminal.pty_process import PtyProcess
from app.terminal.session_registry import (
    create_session,
    ensure_operator_session,
    get_session,
)
from app.terminal.workspace_roots import WorkspaceRootError, resolve_workspace_root


def _decode_output(data: bytes) -> str:
    return data.decode("utf-8", errors="surrogateescape")


async def _send_json(websocket: WebSocket, payload: dict[str, Any]) -> None:
    await websocket.send_text(json.dumps(payload, ensure_ascii=False))


async def handle_terminal_session(
    websocket: WebSocket,
    workspace_id: str,
    *,
    session_id: str = "terminal-operator",
    role: str = "operator",
) -> None:
    await websocket.accept()

    try:
        workspace_root = resolve_workspace_root(workspace_id)
    except WorkspaceRootError as exc:
        await _send_json(websocket, {"type": "error", "message": str(exc)})
        await websocket.close(code=4400)
        return

    clean_session_id = str(session_id or "terminal-operator").strip() or "terminal-operator"
    clean_role = str(role or "operator").strip().lower() or "operator"
    session = get_session(workspace_id, clean_session_id)
    if session is None:
        if clean_session_id == "terminal-operator":
            session = ensure_operator_session(workspace_id)
        else:
            session = create_session(
                workspace_id=workspace_id,
                role=clean_role,
                session_id=clean_session_id,
            )

    pty = PtyProcess(str(workspace_root), session_id=session.session_id)
    loop = asyncio.get_running_loop()
    output_queue: asyncio.Queue[bytes | None] = asyncio.Queue()

    def on_output(chunk: bytes) -> None:
        output_queue.put_nowait(chunk)

    def on_closed() -> None:
        output_queue.put_nowait(None)

    pty.attach_reader(loop, on_output, on_closed)
    writer_task = asyncio.create_task(_pump_output(websocket, output_queue))

    await _send_json(
        websocket,
        {
            "type": "ready",
            "workspace_id": workspace_id,
            "workspace_root": str(workspace_root),
            "session_id": session.session_id,
            "role": session.role,
            "title": session.title,
        },
    )

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                pty.write(raw.encode("utf-8"))
                continue

            msg_type = message.get("type")
            if msg_type == "input":
                data = message.get("data", "")
                if isinstance(data, str):
                    pty.write(data.encode("utf-8"))
            elif msg_type == "resize":
                pty.resize(int(message.get("cols", 80)), int(message.get("rows", 24)))
            elif msg_type == "close":
                break
            elif msg_type == "ping":
                await _send_json(websocket, {"type": "pong"})
    except WebSocketDisconnect:
        pass
    finally:
        writer_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await writer_task
        pty.detach_reader(loop)
        pty.close()


async def _pump_output(websocket: WebSocket, output_queue: asyncio.Queue[bytes | None]) -> None:
    while True:
        chunk = await output_queue.get()
        if chunk is None:
            await _send_json(websocket, {"type": "closed"})
            break
        await _send_json(websocket, {"type": "output", "data": _decode_output(chunk)})
