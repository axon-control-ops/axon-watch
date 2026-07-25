"""Gate 2 request identity (revocable principal for mutating APIs)."""

from __future__ import annotations

from contextvars import ContextVar

_request_identity: ContextVar[str] = ContextVar("axon_request_identity", default="anonymous")


def get_request_identity() -> str:
    return str(_request_identity.get() or "anonymous")


def reset_request_identity(identity: str = "anonymous") -> None:
    _request_identity.set(str(identity or "anonymous").strip() or "anonymous")


def bind_request_identity(identity: str):
    """Return a context-var token for try/finally reset."""
    return _request_identity.set(str(identity or "anonymous").strip() or "anonymous")


def reset_identity_token(token) -> None:
    _request_identity.reset(token)
