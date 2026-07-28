"""Gate 2 authentication and containment helpers."""

from __future__ import annotations

from app.auth.audit import append_auth_audit
from app.auth.identity import get_request_identity
from app.auth.middleware import MutatingAuthMiddleware
from app.auth.settings import (
    auth_mode,
    configured_auth_mode,
    is_remotely_reachable,
    operator_token,
    vault_auto_unlock_allowed,
)
from app.auth.step_up import (
    EXACT_EFFECT_ACTION,
    FULL_ACCESS_ACTION,
    reject_missing_step_up,
)

__all__ = [
    "EXACT_EFFECT_ACTION",
    "FULL_ACCESS_ACTION",
    "MutatingAuthMiddleware",
    "append_auth_audit",
    "auth_mode",
    "configured_auth_mode",
    "get_request_identity",
    "is_remotely_reachable",
    "operator_token",
    "reject_missing_step_up",
    "vault_auto_unlock_allowed",
]
