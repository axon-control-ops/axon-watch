"""Live operational Markdown. Never dump the source prompt."""

from __future__ import annotations

from typing import Any

from app.platform_recovery.projection import project_run_item
from app.persistence import run_store


def _bullets(values: list[str]) -> str:
    items = [item.strip() for item in values if item and item.strip()]
    if not items:
        return "- None"
    return "\n".join(f"- {item}" for item in items)


def _state_section(item: dict[str, Any]) -> str:
    bucket = str(item.get("bucket") or "")
    action = item.get("recovery_action") if isinstance(item.get("recovery_action"), dict) else {}
    if bucket == "ACTIVE":
        return "\n".join(
            (
                "## Current Activity",
                "",
                "The agent is actively working.",
                "",
                "### Last Meaningful Progress",
                "",
                str(item.get("last_meaningful_progress") or "No checkpoint yet."),
                "",
                "### Current Stage",
                "",
                str(item.get("phase") or "unknown"),
                "",
                "### Expected Next Transition",
                "",
                str(action.get("summary") or "Continue until verification."),
            )
        )
    if bucket == "STALE":
        return "\n".join(
            (
                "## Recovery Required",
                "",
                "This run has stopped demonstrating meaningful progress.",
                "",
                "### Why",
                "",
                str(item.get("why_stale") or "unknown"),
                "",
                "### Last Known Progress",
                "",
                str(item.get("last_meaningful_progress") or "None recorded."),
                "",
                "### Recommended Action",
                "",
                str(action.get("summary") or "Inspect evidence."),
                "",
                "### Recovery Options",
                "",
                "- Resume",
                "- Retry",
                "- Cancel",
                "- Inspect evidence",
            )
        )
    if bucket == "FAILED":
        return "\n".join(
            (
                "## Failure",
                "",
                "### Root Cause",
                "",
                str(item.get("failure_class") or "UNKNOWN"),
                "",
                "### Evidence",
                "",
                str(item.get("what_happened") or "No receipt summary."),
                "",
                "### Recommended Fix",
                "",
                str(action.get("summary") or "Inspect evidence."),
                "",
                "### Retry Safety",
                "",
                "Safe" if action.get("safe") else "Unsafe / Requires approval",
            )
        )
    if bucket == "BLOCKED":
        return "\n".join(
            (
                "## Blocked",
                "",
                "### Blocking Condition",
                "",
                str(item.get("what_happened") or "Awaiting a human decision."),
                "",
                "### Required Human Action",
                "",
                str(action.get("summary") or "Approve or reject the pending request."),
                "",
                "### What Will Happen After Resolution",
                "",
                "The run will resume from the current checkpoint, not from a blank retry.",
            )
        )
    if str(item.get("phase")) == "completed":
        return "\n".join(
            (
                "## Verified Complete",
                "",
                "### Verified",
                "",
                str(item.get("what_happened") or "Run completed."),
                "",
                "### Evidence",
                "",
                f"Run `{item.get('run_id')}`",
                "",
                "### Follow-up",
                "",
                "Reconcile operator-facing state if a stale banner remains.",
            )
        )
    return f"## Current Blocker\n\n{action.get('summary') or 'None'}"


def build_operational_instructions(
    *,
    workspace_id: str,
    run_id: str | None = None,
    agent: str | None = None,
) -> str:
    record = None
    if run_id:
        record = run_store.get_run(run_id)
    if record is None:
        for candidate in run_store.list_runs():
            if str(candidate.get("workspace_id") or "") != workspace_id:
                continue
            if agent and str(candidate.get("employee_role") or "") != agent:
                continue
            record = candidate
            break
    if record is None:
        return (
            "# Current Task\n\n"
            "## Objective\n\n"
            "No live run is selected.\n\n"
            "## Current State\n\n"
            "- Status: idle\n"
            f"- Workspace: `{workspace_id}`\n"
            "- Evidence state: none\n\n"
            "## Recommended Next Step\n\n"
            "1. Choose a task or start a run.\n"
            "2. Keep this panel for live operational state, not the original prompt.\n"
        )
    item = project_run_item(record)
    action = item.get("recovery_action") if isinstance(item.get("recovery_action"), dict) else {}
    verified = []
    unverified = []
    if item.get("current_checkpoint"):
        verified.append(f"Checkpoint `{item['current_checkpoint'].get('last_checkpoint_at')}`")
    else:
        unverified.append("No checkpoint")
    if str(item.get("phase")) == "completed":
        verified.append("Run phase is completed")
    else:
        unverified.append("Final verification")
    markdown = "\n".join(
        (
            "# Current Task",
            "",
            "## Objective",
            "",
            str(record.get("summary") or "Continue the selected run safely."),
            "",
            "## Current State",
            "",
            f"- Status: {item.get('bucket')} ({item.get('phase')})",
            f"- Agent: {item.get('agent') or 'unassigned'}",
            f"- Run: `{item.get('run_id')}`",
            f"- Task: `{item.get('task_id') or 'none'}`",
            f"- Workspace: `{workspace_id}`",
            f"- Last activity: {item.get('last_heartbeat') or 'unknown'}",
            f"- Evidence state: {item.get('failure_class')}",
            "",
            "## What Has Been Verified",
            "",
            _bullets(verified),
            "",
            "## What Is Not Yet Verified",
            "",
            _bullets(unverified),
            "",
            _state_section(item),
            "",
            "## Recommended Next Step",
            "",
            f"1. {action.get('summary') or 'Inspect the Recovery Center item.'}",
            "2. Use only the recovery actions valid for this state.",
            "3. Verify with the repository command below after any recovery.",
            "",
            "## Recovery",
            "",
            "If the task is stale or blocked:",
            "",
            "1. Open Recovery Center.",
            "2. Choose Reconcile, Resume, Retry, or Cancel — never a destructive Clear.",
            "3. Confirm the new receipt before assuming success.",
            "",
            "## Safe Actions",
            "",
            _bullets(item.get("actions") or ["Inspect"]),
            "",
            "## Approval Required",
            "",
            _bullets(
                [] if action.get("safe") else [str(action.get("authority") or "HUMAN_APPROVAL")]
            ),
            "",
            "## Verification",
            "",
            "Run:",
            "",
            "```text",
            "npm run verify:clean-baseline",
            "```",
            "",
            "Expected result:",
            "",
            "```text",
            "CLEAN BASELINE PASS",
            "```",
            "",
            "## Do Not",
            "",
            "* Do not treat UI appearance as success.",
            "* Do not delete historical run evidence.",
            "* Do not retry an UNKNOWN or AUTH failure in a loop.",
            "",
            "## Evidence",
            "",
            f"* Run: `{item.get('run_id')}`",
            f"* Task: `{item.get('task_id') or 'none'}`",
            f"* Receipt: `{record.get('history_ref') or 'none'}`",
            f"* Verification: `{((item.get('current_checkpoint') or {}).get('verification_state') or 'none')}`",
            "",
            "## Completion Criteria",
            "",
            "* [ ] Implementation complete",
            "* [ ] Tests pass",
            "* [ ] Verification passes",
            "* [ ] No stale workers remain",
            "* [ ] Evidence recorded",
            "* [ ] Operator-facing state reconciled",
            "",
        )
    )
    return markdown if markdown.endswith("\n") else f"{markdown}\n"
