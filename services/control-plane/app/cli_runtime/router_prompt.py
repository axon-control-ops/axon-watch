"""Prompt assembly for the chat/composer agent path.

Split out of ``router.py`` per its ratchet target.
"""

from __future__ import annotations

from app.chat.scanned_workbook_gate import assignment_workbook_policy_appendix
from app.research.availability import research_capability_snapshot
from app.workspace_agents.watcher_receipts import chat_watcher_receipts_section

def build_agent_prompt(
    *,
    composer_mode: str,
    user_prompt: str,
    context_block: str,
    execution_tier: str = "consultative",
    research_snapshot: dict[str, object] | None = None,
    write_scope_hint: str = "",
    workspace_id: str = "",
    instructions_context: object | None = None,
) -> str:
    from app.workspace_agents.employee_persona_prompt import (
        adapt_lane_b_system_prompt_for_employee,
        split_employee_persona_from_context,
    )

    from app.cli_runtime.router import _sentry_monitor_context, _system_prompt

    snapshot = research_snapshot or research_capability_snapshot()
    workbook_policy = assignment_workbook_policy_appendix(user_prompt, context_block)
    policy_block = f"\n\n{workbook_policy}" if workbook_policy else ""
    system = adapt_lane_b_system_prompt_for_employee(
        _system_prompt(
            composer_mode,
            execution_tier,
            research_snapshot=snapshot,
            instructions_context=instructions_context,
        ),
        context_block,
    )
    persona_block, remainder_context = split_employee_persona_from_context(context_block)
    persona_section = f"\n\n{persona_block}" if persona_block else ""
    workspace_body = remainder_context if persona_block else context_block
    sentry_context = _sentry_monitor_context(user_prompt)
    sentry_section = f"\n\n{sentry_context}" if sentry_context else ""
    scope_section = f"\n\nSandbox write scope: {write_scope_hint}" if write_scope_hint else ""
    watcher_section = chat_watcher_receipts_section(workspace_id, user_prompt)
    return (
        f"{system}"
        f"{policy_block}"
        f"{persona_section}\n\n"
        f"Workspace context:\n{workspace_body}\n\n"
        f"{sentry_section}"
        f"{watcher_section}"
        f"{scope_section}\n\n"
        f"Operator request:\n{user_prompt.strip()}"
    )

__all__ = ["build_agent_prompt"]
