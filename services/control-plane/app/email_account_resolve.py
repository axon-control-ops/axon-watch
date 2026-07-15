"""Resolve the configured mailbox for a workspace send path."""

from __future__ import annotations

from typing import Any


def resolve_workspace_email_account(
    settings: dict[str, Any],
    *,
    workspace_id: str = "",
    account_id: str = "",
) -> dict[str, Any] | None:
    """Prefer the workspace mailbox; fall back to an explicit account id."""

    accounts = [
        entry for entry in (settings.get("accounts") or []) if isinstance(entry, dict)
    ]
    workspace = str(workspace_id or "").strip()
    if workspace:
        for entry in accounts:
            if str(entry.get("workspace_id") or "").strip() == workspace:
                return entry
    account = str(account_id or "").strip()
    if account:
        for entry in accounts:
            if str(entry.get("account_id") or "").strip() == account:
                return entry
    return None
