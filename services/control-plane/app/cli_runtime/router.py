"""Runtime routing for IDE composer requests."""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from app.adapters.watch_client import fetch_watch_monitors
from app.cli_runtime.approval_gate import (
    consultative_only_notice,
    resolve_runtime_execution_tier,
)
from app.cli_runtime.catalog import runtime_status_snapshot
from app.cli_runtime.codex_models import default_codex_model
from app.cli_runtime.mcp_registry import mcp_tools_for_composer_mode
from app.cli_runtime.non_cursor_dispatch import run_non_cursor_local
from app.cli_runtime.runtime_candidates import effective_cli_model, ordered_candidates_for_dispatch
from app.cli_runtime.runtime_failure import (
    fallback_reply as _fallback_reply,
    runtime_unready_reason as _runtime_unready_reason,
)
from app.cli_runtime.sentry_context import sentry_monitor_context
from app.cli_runtime.subprocess_runner import RuntimeProcessStoppedError
from app.cli_runtime.sandbox_policy_adapter import prepare_execution_sandbox
from app.cli_runtime.cursor_agent import (
    CursorAgentReply,
    run_cursor_local,
    run_cursor_local_with_recursion_retry,
)
from app.cli_runtime.runtime_auth import (
    claude_dispatch_env,
    codex_dispatch_env,
    cursor_dispatch_env,
    env_has_api_key,
    env_without_api_keys,
    looks_like_auth_error,
    summarize_auth_error,
)
from app.cli_runtime.vault_keys import runtime_subprocess_env
from app.cli_runtime.research_mcp import ensure_workspace_research_mcp
from app.chat.scanned_workbook_gate import assignment_workbook_policy_appendix
from app.debug_prompt import build_debug_system_prompt
from app.kairo_ask_prompt import build_ask_system_prompt
from app.cli_runtime.long_running_shell_prompt import LONG_RUNNING_SHELL_CLAUSE
from app.cli_runtime.plan_system_prompt import (
    ask_fence_instruction,
    build_plan_system_prompt,
)
from app.workspace_agents.critical_review_clause import append_critical_review_clause
from app.workspace_agents.execution_policy import AgentExecutionPolicy
from app.research.availability import format_capability_line, research_capability_snapshot
from app.persistence.operator_presence_settings_store import load_settings
from app.runs.service import RunNotFoundError, get_run
from app.terminal.workspace_roots import WorkspaceRootError, resolve_workspace_root

logger = logging.getLogger(__name__)


_REPLY_STYLE = (
    "Reply in first person. Use plain language anyone can follow — "
    "avoid internal repo jargon such as lane IDs, slice names, or implementation acronyms. "
    "Never address the listener as \"operator\", \"user\", or \"human\". "
    "Before tools or file edits, open a :::thinking fence that states what you will do next "
    "in future tense (one or two short sentences), then close ::: before acting. "
    "Do not wait until after the work to announce the action plan. "
    "Keep the final reply free of retrospective process narration "
    "('I'll review…', 'Drafting…', 'I looked through…')."
)

_INSTRUCTION_TAKING = (
    "Before acting, treat the request as binding Instructions when it includes "
    "Goal / In scope / Out of scope / Steps / Constraints. "
    "Out of scope is strict: if commit, push, merge, release, or git status was not asked for, "
    "do not add those steps, invent desk-clearing git chores, or run git/shell "
    "probes to \"get oriented\". "
    "Mentions like \"I never said anything about committing\" are a refusal, not commit intent. "
    "When committing, never reuse the operator's task instruction as the git -m subject; "
    "write a short diff-based summary of what changed (files/intent), or use an explicitly "
    "quoted commit message when the operator provided one."
)

def _sentry_monitor_context(user_prompt: str) -> str:
    return sentry_monitor_context(
        user_prompt,
        fetch_monitors=fetch_watch_monitors,
    )

def _operator_persona_enabled() -> bool:
    return bool(load_settings().get("operator_persona_enabled", True))


def _system_prompt(
    composer_mode: str,
    execution_tier: str = "consultative",
    *,
    persona_enabled: bool | None = None,
    research_snapshot: dict[str, object] | None = None,
) -> str:
    research_line = format_capability_line(research_snapshot or research_capability_snapshot())
    if composer_mode == "ask":
        enabled = persona_enabled if persona_enabled is not None else _operator_persona_enabled()
        return f"{build_ask_system_prompt(persona_enabled=enabled)} {research_line}"
    if composer_mode == "plan":
        offline_clause = (
            "Ground the plan in the local repo and provided context. "
            "If online research is unavailable, do not suggest web search as a required step "
            "and note offline limits in ## Sources. "
        )
        if (research_snapshot or research_capability_snapshot()).get("available"):
            offline_clause = (
                "When external or vendor facts are required, call axon_research_search or "
                "axon_research_fetch first. Do not rely on built-in webSearch/webFetch in "
                "this headless runtime. Still ground implementation steps in the local repo. "
            )
        return build_plan_system_prompt(
            offline_clause=offline_clause,
            research_line=research_line,
            instruction_taking=_INSTRUCTION_TAKING,
            reply_style=_REPLY_STYLE,
        )
    if composer_mode == "debug":
        return build_debug_system_prompt(
            execution_tier=execution_tier,
            research_line=research_line,
        )
    if execution_tier == "executing":
        research_clause = ""
        if (research_snapshot or research_capability_snapshot()).get("available"):
            research_clause = (
                "For live web facts, call axon_research_search or axon_research_fetch before citing sources. "
                "Built-in webSearch/webFetch are unavailable in this headless runtime. "
            )
        return append_critical_review_clause(
            "You are Axon-X Lane B in Agent mode with approved execution access. "
            "Use only the paths and audited commands available in this run. Edit files "
            "inside the Project root shown in workspace context as needed. Use "
            "workspace-relative paths such as README.md — never edit Cursor metadata "
            "directories. Do the work first, then reply with a short summary "
            f"of what changed. {ask_fence_instruction()}"
            f"{_INSTRUCTION_TAKING} {LONG_RUNNING_SHELL_CLAUSE} {research_clause}{research_line} {_REPLY_STYLE}"
        )
    return append_critical_review_clause(
        "You are Axon-X Lane B in Agent mode (consultative slice). Answer using the "
        "supplied workspace context, propose concrete next steps, and do not claim you "
        f"edited files or ran commands. {ask_fence_instruction()}"
        f"{_INSTRUCTION_TAKING} {research_line} {_REPLY_STYLE}"
    )
def _build_prompt(
    *,
    composer_mode: str,
    user_prompt: str,
    context_block: str,
    execution_tier: str = "consultative",
    research_snapshot: dict[str, object] | None = None,
) -> str:
    from app.workspace_agents.employee_persona_prompt import (
        adapt_lane_b_system_prompt_for_employee,
        split_employee_persona_from_context,
    )

    snapshot = research_snapshot or research_capability_snapshot()
    workbook_policy = assignment_workbook_policy_appendix(user_prompt, context_block)
    policy_block = f"\n\n{workbook_policy}" if workbook_policy else ""
    system = adapt_lane_b_system_prompt_for_employee(
        _system_prompt(composer_mode, execution_tier, research_snapshot=snapshot),
        context_block,
    )
    persona_block, remainder_context = split_employee_persona_from_context(context_block)
    persona_section = f"\n\n{persona_block}" if persona_block else ""
    workspace_body = remainder_context if persona_block else context_block
    sentry_context = _sentry_monitor_context(user_prompt)
    sentry_section = f"\n\n{sentry_context}" if sentry_context else ""
    return (
        f"{system}"
        f"{policy_block}"
        f"{persona_section}\n\n"
        f"Workspace context:\n{workspace_body}\n\n"
        f"{sentry_section}\n\n"
        f"Operator request:\n{user_prompt.strip()}"
    )
def _resolve_workspace_root(workspace_id: str) -> Path | None:
    try:
        return resolve_workspace_root(workspace_id)
    except WorkspaceRootError:
        return None
def _cloud_runtime_message(record: dict[str, object]) -> str:
    label = str(record.get("label") or record.get("id") or "cloud runtime")
    return (
        f"{label} is configured in the catalog, but its execution adapter has not landed yet. "
        "Use the local runtime target or switch the default runtime back to a local CLI."
    )


def _split_codex_model_selection(model: str) -> tuple[str, str]:
    """Decode the UI's model@effort preference into Codex CLI arguments."""
    selected = str(model or "").strip()
    model_id, marker, effort = selected.rpartition("@")
    if marker and model_id and effort in {"low", "medium", "high", "xhigh"}:
        return model_id, effort
    return selected, ""


def _run_phase(run_id: str) -> str | None:
    trimmed = str(run_id or "").strip()
    if not trimmed:
        return None
    try:
        record = get_run(trimmed)
    except RunNotFoundError:
        return None
    return str(record.get("phase") or "") or None


def _attach_dispatch_metadata(result: dict[str, object], *, composer_mode: str) -> dict[str, object]:
    return {**result, "mcp_tools": mcp_tools_for_composer_mode(composer_mode)}


def _cursor_reply_content(reply: CursorAgentReply, approval_notice: str | None) -> str:
    content = reply.content
    if approval_notice:
        content = f"{content.rstrip()}\n\n---\n{approval_notice}"
    return content


def dispatch_ide_composer(
    *,
    workspace_id: str,
    composer_mode: str,
    user_prompt: str,
    context_block: str,
    run_id: str = "",
    runtime_target: str | None = None,
    runtime_model: str | None = None,
    execution_access: str | None = None,
    on_chunk: Callable[[str, str], None] | None = None,
    cursor_trust_policy: str = "operator",
    workspace_root: Path | None = None,
    execution_policy: AgentExecutionPolicy | None = None,
) -> dict[str, object]:
    def _finish(payload: dict[str, object]) -> dict[str, object]:
        return _attach_dispatch_metadata(payload, composer_mode=composer_mode)

    subprocess_env = runtime_subprocess_env()
    snapshot = runtime_status_snapshot(
        force_refresh=bool(subprocess_env.get("CURSOR_API_KEY")),
    )
    resolved_root = workspace_root if workspace_root is not None else _resolve_workspace_root(workspace_id)
    if resolved_root is None:
        return _finish({
            "content": _fallback_reply(
                composer_mode=composer_mode,
                user_prompt=user_prompt,
                context_block=context_block,
                reason="workspace root unavailable",
            ),
            "dispatched": False,
            "runtime_id": "",
            "runtime_label": "",
            "reason": "workspace root unavailable",
        })
    workspace_root = resolved_root

    run_phase = _run_phase(run_id)
    execution_tier = resolve_runtime_execution_tier(
        composer_mode=composer_mode,
        run_phase=run_phase,
        execution_access=execution_access,
    )
    research_snapshot = research_capability_snapshot()
    if workspace_root is not None:
        ensure_workspace_research_mcp(workspace_root)
    prompt = _build_prompt(
        composer_mode=composer_mode,
        user_prompt=user_prompt,
        context_block=context_block,
        execution_tier=execution_tier,
        research_snapshot=research_snapshot,
    )
    approval_notice = consultative_only_notice(
        composer_mode=composer_mode,
        run_phase=run_phase,
        execution_access=execution_access,
    )
    errors: list[str] = []
    ready_run_errors: list[str] = []
    last_ready_runtime_label = ""
    ordered_candidates = ordered_candidates_for_dispatch(snapshot, runtime_target)
    # The model pin travels with the family it was chosen for. Candidates are
    # already ordered preferred-first, so the first candidate's family is the
    # one `runtime_model` was picked against — carrying it into a fallback of
    # a *different* family (e.g. a Cursor model id sent to the Codex CLI) is
    # what broke fallback dispatch; scope it to same-family candidates only.
    preferred_family = str(ordered_candidates[0].get("family") or "") if ordered_candidates else ""

    for record in ordered_candidates:
        runtime_id = str(record.get("id") or "")
        if not record.get("ready"):
            errors.append(_runtime_unready_reason(record))
            continue
        binary = str(record.get("binary") or "")
        family = str(record.get("family") or "")
        target_type = str(record.get("target_type") or "local")
        candidate_runtime_model = runtime_model if family == preferred_family else ""
        model = effective_cli_model(family, str(candidate_runtime_model or ""))
        reasoning_effort = ""
        runtime_label = str(record.get("label") or runtime_id)
        dispatch_env = subprocess_env
        if family == "cursor":
            dispatch_env = cursor_dispatch_env(
                subprocess_env,
                auth=record.get("auth") if isinstance(record.get("auth"), dict) else None,
            )
        elif family == "claude":
            dispatch_env = claude_dispatch_env(
                subprocess_env,
                auth=record.get("auth") if isinstance(record.get("auth"), dict) else None,
            )
        elif family == "codex":
            model, reasoning_effort = _split_codex_model_selection(model)
            dispatch_env = codex_dispatch_env(
                subprocess_env,
                auth=record.get("auth") if isinstance(record.get("auth"), dict) else None,
            )
            if not model:
                model = default_codex_model(binary, env=dispatch_env)
        dispatch_env, sandbox_policy = prepare_execution_sandbox(
            execution_policy,
            family=family,
            runtime_binary=binary,
            env=dispatch_env,
            workspace_id=workspace_id,
            run_id=run_id,
        )
        try:
            if target_type == "cloud":
                raise RuntimeError(_cloud_runtime_message(record))
            if family == "cursor":
                cursor_reply = run_cursor_local_with_recursion_retry(
                    runtime_id=runtime_id,
                    workspace_id=workspace_id,
                    binary=binary,
                    prompt=prompt,
                    workspace_root=workspace_root,
                    composer_mode=composer_mode,
                    execution_tier=execution_tier,
                    model=model,
                    subprocess_env=dispatch_env,
                    run_id=run_id,
                    on_chunk=on_chunk,
                    trust_policy=cursor_trust_policy,
                    sandbox_policy=sandbox_policy,
                )
                content = _cursor_reply_content(cursor_reply, approval_notice)
                return _finish({
                    "content": content,
                    "dispatched": True,
                    "runtime_id": runtime_id,
                    "runtime_label": runtime_label,
                    "reason": "",
                    "execution_tier": execution_tier,
                    "generated_image_paths": list(cursor_reply.generated_image_paths),
                })
            if family in {"claude", "codex"}:
                content = run_non_cursor_local(
                    family=family,
                    binary=binary,
                    prompt=prompt,
                    workspace_root=workspace_root,
                    composer_mode=composer_mode,
                    execution_tier=execution_tier,
                    model=model,
                    reasoning_effort=reasoning_effort,
                    subprocess_env=dispatch_env,
                    run_id=run_id,
                    on_chunk=on_chunk,
                    approval_notice=approval_notice,
                    sandbox_policy=sandbox_policy,
                )
                return _finish({
                    "content": content,
                    "dispatched": True,
                    "runtime_id": runtime_id,
                    "runtime_label": runtime_label,
                    "reason": "",
                    "execution_tier": execution_tier,
                })
        except RuntimeError as exc:
            if isinstance(exc, RuntimeProcessStoppedError):
                return _finish({
                    "content": _fallback_reply(
                        composer_mode=composer_mode,
                        user_prompt=user_prompt,
                        context_block=context_block,
                        reason=str(exc),
                        failure_phase="run_error",
                        runtime_label=runtime_label,
                    ),
                    "dispatched": False,
                    "runtime_id": runtime_id,
                    "runtime_label": runtime_label,
                    "reason": str(exc),
                    "stopped": True,
                    "failure_phase": "run_error",
                })
            detail = str(exc)
            logger.exception(
                "lane_b_dispatch_failed runtime_id=%s family=%s composer_mode=%s "
                "workspace_id=%s exc_type=%s",
                runtime_id,
                family,
                composer_mode,
                workspace_id,
                type(exc).__name__,
            )
            if looks_like_auth_error(detail) and env_has_api_key(dispatch_env, family=family):
                retry_env = env_without_api_keys(dispatch_env, family=family)
                if retry_env != dispatch_env:
                    try:
                        if family == "cursor":
                            cursor_reply = run_cursor_local(
                                binary=binary,
                                prompt=prompt,
                                workspace_root=workspace_root,
                                composer_mode=composer_mode,
                                execution_tier=execution_tier,
                                model=model,
                                subprocess_env=retry_env,
                                run_id=run_id,
                                on_chunk=on_chunk,
                                trust_policy=cursor_trust_policy,
                                sandbox_policy=sandbox_policy,
                            )
                            content = _cursor_reply_content(cursor_reply, approval_notice)
                        else:
                            content = run_non_cursor_local(
                                family=family,
                                binary=binary,
                                prompt=prompt,
                                workspace_root=workspace_root,
                                composer_mode=composer_mode,
                                execution_tier=execution_tier,
                                model=model,
                                reasoning_effort=reasoning_effort,
                                subprocess_env=retry_env,
                                run_id=run_id,
                                on_chunk=on_chunk,
                                approval_notice=approval_notice,
                                sandbox_policy=sandbox_policy,
                            )
                        payload = {
                            "content": content,
                            "dispatched": True,
                            "runtime_id": runtime_id,
                            "runtime_label": runtime_label,
                            "reason": "",
                            "execution_tier": execution_tier,
                        }
                        if family == "cursor":
                            payload["generated_image_paths"] = list(cursor_reply.generated_image_paths)
                        return _finish(payload)
                    except RuntimeError as retry_exc:
                        detail = str(retry_exc)
                        logger.exception(
                            "lane_b_dispatch_auth_retry_failed runtime_id=%s family=%s",
                            runtime_id,
                            family,
                        )
            summarized = summarize_auth_error(
                family=family,
                detail=detail,
                had_api_key=env_has_api_key(dispatch_env, family=family),
            )
            errors.append(summarized)
            ready_run_errors.append(summarized)
            last_ready_runtime_label = runtime_label

    reason = "; ".join(item for item in errors if item) or "no CLI runtime is installed"
    failure_phase = "run_error" if ready_run_errors else "not_ready"
    # When a ready runtime actually failed, don't bury that under skipped "unavailable" peers.
    if failure_phase == "run_error" and ready_run_errors:
        reason = "; ".join(item for item in ready_run_errors if item) or reason
    return _finish({
        "content": _fallback_reply(
            composer_mode=composer_mode,
            user_prompt=user_prompt,
            context_block=context_block,
            reason=reason,
            failure_phase=failure_phase,
            runtime_label=last_ready_runtime_label,
        ),
        "dispatched": False,
        "runtime_id": "",
        "runtime_label": "",
        "reason": reason,
        "failure_phase": failure_phase,
    })


def route_ide_composer(
    *,
    workspace_id: str,
    composer_mode: str,
    user_prompt: str,
    context_block: str,
) -> str:
    return str(
        dispatch_ide_composer(
            workspace_id=workspace_id,
            composer_mode=composer_mode,
            user_prompt=user_prompt,
            context_block=context_block,
        ).get("content")
        or ""
    )
