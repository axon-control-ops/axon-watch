"""Auto-start skip gates for continuous worker ticks (usage + runtime auth)."""

from __future__ import annotations

from app.workspace_agents.failure_detail import is_runtime_auth_failure, is_usage_limit_failure
from app.workspace_agents.run_outcome import latest_role_run_outcome


def usage_limit_blocks_auto_start(workspace_id: str, role: str) -> bool:
    """Skip auto-schedule for this role when its last shift failed on usage limits.

    Soft-open when the runtime that *actually failed* still shows headroom.
    ``is_usage_limit_failure`` matches generic phrasing ("usage limit", "out of
    usage", ...) that both Cursor and Claude Code can produce, but this used
    to always consult Cursor's pool regardless of which CLI failed — so a
    Claude usage-limit failure could never soft-open (Claude never has Cursor
    headroom) and, worse, could falsely soft-open off leftover Cursor
    headroom that has nothing to do with the Claude block. Route to the probe
    for the runtime named in the failure detail instead.
    """
    outcome = latest_role_run_outcome(workspace_id, role)
    if not outcome or str(outcome.get("outcome") or "").strip().lower() != "failed":
        return False
    detail = str(outcome.get("detail") or "")
    if not is_usage_limit_failure(detail):
        return False

    lowered = detail.lower()
    try:
        if "claude" in lowered:
            from app.cli_runtime.claude_usage_probe import (
                claude_usage_allows_agent_retry,
                probe_claude_usage,
                record_claude_usage_limit_hit,
            )

            record_claude_usage_limit_hit(detail)
            if claude_usage_allows_agent_retry(probe_claude_usage()):
                return False
        else:
            # Cursor remains the default/legacy source of this failure shape;
            # unknown runtimes fall back to the Cursor pool check too.
            from app.cli_runtime.cursor_usage_probe import (
                cursor_usage_allows_agent_retry,
                probe_cursor_usage,
            )

            if cursor_usage_allows_agent_retry(probe_cursor_usage()):
                return False
    except Exception:
        pass
    return True


def workspace_usage_limit_blocks_auto_start(workspace_id: str, roles: list[str]) -> bool:
    """Deprecated account-wide gate — kept for import compatibility; always False.

    Cursor pools are not a single hard stop for every role when Auto/on-demand remain.
    """
    del workspace_id, roles
    return False


def runtime_auth_blocks_auto_start(workspace_id: str, role: str) -> bool:
    """Skip auto-schedule when the last shift failed on missing CLI/vault auth.

    Soft-open after a successful Cursor auth heal — probe timeouts should not
    permanently quarantine a role once the host CLI is signed in again.
    """
    outcome = latest_role_run_outcome(workspace_id, role)
    if not outcome or str(outcome.get("outcome") or "").strip().lower() != "failed":
        return False
    detail = str(outcome.get("detail") or "")
    if not is_runtime_auth_failure(detail):
        return False
    try:
        from app.cli_runtime.catalog_snapshot import (
            recover_cursor_auth_synchronously,
            snapshot_has_auth_probe_timeout,
        )
        from app.cli_runtime.readiness import summarize_cli_runtime_readiness

        if "auth probe timed out" in detail.lower() or "timed out" in detail.lower():
            snapshot = recover_cursor_auth_synchronously()
            summary = summarize_cli_runtime_readiness(snapshot)
            if bool(summary.get("dispatch_ready")) and not snapshot_has_auth_probe_timeout(
                snapshot
            ):
                return False
    except Exception:
        pass
    return True
