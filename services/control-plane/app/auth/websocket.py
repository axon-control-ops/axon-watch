"""WebSocket authentication helpers for operator-controlled channels."""

from __future__ import annotations

import json

from fastapi import WebSocket

from app.auth.middleware import resolve_operator_identity


async def authorize_operator_websocket(websocket: WebSocket, *, resource: str) -> str | None:
    """Return the resolved identity, or close the socket with an auth error."""
    client_host = websocket.client.host if websocket.client else None
    identity, error = resolve_operator_identity(websocket.headers, websocket.cookies, client_host)
    if identity is not None:
        return identity

    await websocket.accept()
    await websocket.send_text(
        json.dumps(
            {
                "type": "error",
                "message": error or f"{resource} requires operator authentication",
                "auth_required": True,
            },
            ensure_ascii=False,
        )
    )
    await websocket.close(code=4401)
    return None
