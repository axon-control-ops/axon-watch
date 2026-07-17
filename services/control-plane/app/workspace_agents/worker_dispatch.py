"""Headless Lane B dispatch for scheduled employee-agent runs."""

from __future__ import annotations

import logging
import os
from typing import Any

from app.chat.lane_b_agent import LaneBContext, generate_lane_b_result
from app.chat.lane_b_stream_execute import finalize_lane_b_agent_run
from app.terminal.session_registry import ensure_agent_session
from app.workspace_agents.config_loader import EmployeeConfig
from app.workspace_agents.worker_prompt import build_continuous_worker_prompt

logger = logging.getLogger(__name__)


def worker_dispatch_enabled() -> bool:
    raw = os.environ.get("AXON_WATCH_WORKER_SCHEDULER_DISPATCH", "1").strip().lower()
    return raw not in {"0", "false", "off", "no"}


def dispatch_continuous_worker_run(
    *,
    workspace_id: str,
    employee: EmployeeConfig,
    run_record: dict[str, Any],
) -> tuple[bool, dict[str, Any] | None]:
    """Run one bounded Lane B shift for a role-tagged worker run."""
    run_id = str(run_record.get("run_id") or "").strip()
    if not run_id:
        return False, None

    prompt = build_continuous_worker_prompt(workspace_id=workspace_id, employee=employee)
    ensure_agent_session(workspace_id=workspace_id, run_id=run_id)
    context = LaneBContext(workspace_id=workspace_id, composer_mode="agent")
    lane_b_result = generate_lane_b_result(
        context=context,
        user_prompt=prompt,
        run_id=run_id,
        execution_access="full",
    )
    dispatched, finalized = finalize_lane_b_agent_run(
        dispatch_run_id=run_id,
        lane_b_result=lane_b_result,
    )
    if not dispatched:
        logger.warning(
            "continuous worker dispatch fallback for %s role=%s: %s",
            run_id,
            employee.role,
            lane_b_result.get("reason") or lane_b_result.get("content"),
        )
    return dispatched, finalized
