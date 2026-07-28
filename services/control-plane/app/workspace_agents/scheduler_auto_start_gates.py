"""Auto-start skip gates for continuous worker ticks (usage + runtime auth)."""

from __future__ import annotations

import json
import time
from pathlib import Path

from app.workspace_agents.failure_detail import is_runtime_auth_failure, is_usage_limit_failure
from app.workspace_agents.run_outcome import latest_role_run_outcome

_DEBUG_LOG = Path(__file__).resolve().parents[4] / ".cursor" / "debug-bef50e.log"


def _debug_log(hypothesis_id: str, location: str, message: str, data: dict) -> None:
    # #region agent log
    try:
        payload = {
            "sessionId": "bef50e",
            "runId": "usage-gate",
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data,
            "timestamp": int(time.time() * 1000),
        }
        _DEBUG_LOG.parent.mkdir(parents=True, exist_ok=True)
        with _DEBUG_LOG.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, separators=(",", ":")) + "\n")
    except Exception:
        pass
    # #endregion


def usage_limit_blocks_auto_start(workspace_id: str, role: str) -> bool:
    """Skip auto-schedule for this role when its last shift failed on usage limits.

    Soft-open when live Cursor usage still shows Auto headroom or on-demand spend.
    """
    outcome = latest_role_run_outcome(workspace_id, role)
    if not outcome or str(outcome.get("outcome") or "").strip().lower() != "failed":
        return False
    detail = str(outcome.get("detail") or "")
    if not is_usage_limit_failure(detail):
        return False
    try:
        from app.cli_runtime.cursor_usage_probe import (
            cursor_usage_allows_agent_retry,
            probe_cursor_usage,
        )

        usage = probe_cursor_usage()
        if cursor_usage_allows_agent_retry(usage):
            _debug_log(
                "C",
                "scheduler_auto_start_gates.py:usage",
                "role usage soft-open",
                {
                    "workspace_id": workspace_id,
                    "role": role,
                    "auto": usage.get("auto_percent_used"),
                    "on_demand": usage.get("on_demand_enabled"),
                    "blocked": False,
                },
            )
            return False
    except Exception:
        pass
    _debug_log(
        "C",
        "scheduler_auto_start_gates.py:usage",
        "role usage hard-block",
        {"workspace_id": workspace_id, "role": role, "blocked": True},
    )
    return True


def workspace_usage_limit_blocks_auto_start(workspace_id: str, roles: list[str]) -> bool:
    """Deprecated account-wide gate — kept for import compatibility; always False.

    Cursor pools are not a single hard stop for every role when Auto/on-demand remain.
    """
    del workspace_id, roles
    return False


def runtime_auth_blocks_auto_start(workspace_id: str, role: str) -> bool:
    """Skip auto-schedule when the last shift failed on missing CLI/vault auth."""
    outcome = latest_role_run_outcome(workspace_id, role)
    if not outcome or str(outcome.get("outcome") or "").strip().lower() != "failed":
        return False
    return is_runtime_auth_failure(str(outcome.get("detail") or ""))
