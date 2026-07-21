"""Runtime routing for IDE composer requests."""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path

from app.cli_runtime.approval_gate import (
    consultative_only_notice,
    resolve_runtime_execution_tier,
)
from app.cli_runtime.catalog import runtime_status_snapshot
from app.cli_runtime.codex_agent import run_codex_local
from app.cli_runtime.mcp_registry import mcp_tools_for_composer_mode
from app.cli_runtime.recovery import ordered_runtime_candidates
from app.cli_runtime.subprocess_runner import RuntimeProcessStoppedError
from app.cli_runtime.cursor_agent import CursorAgentReply, run_cursor_local
from app.cli_runtime.runtime_auth import (
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
from app.cli_runtime.plan_system_prompt import (
    ask_fence_instruction,
    build_plan_system_prompt,
)
from app.workspace_agents.critical_review_clause import append_critical_review_clause
from app.research.availability import format_capability_line, research_capability_snapshot
from app.persistence.operator_presence_settings_store import load_settings
from app.runs.service import RunNotFoundError, get_run
from app.terminal.workspace_roots import WorkspaceRootError, resolve_workspace_root


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
    "Mentions like \"I never said anything about committing\" are a refusal, not commit intent."
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
            "You are Axon-X Lane B in Agent mode with Full Access. Tool execution is "
            "allowed: edit files and run commands inside the Project root shown in "
            "workspace context as needed to complete the request now. Use "
            "workspace-relative paths such as README.md — never edit Cursor metadata "
            "directories. Do the work first, then reply with a short summary "
            f"of what changed. {ask_fence_instruction()}"
            f"{_INSTRUCTION_TAKING} {research_clause}{research_line} {_REPLY_STYLE}"
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
    return (
        f"{system}"
        f"{policy_block}"
        f"{persona_section}\n\n"
        f"Workspace context:\n{workspace_body}\n\n"
        f"Operator request:\n{user_prompt.strip()}"
    )


def _runtime_unready_reason(record: dict[str, object]) -> str:
    runtime_id = str(record.get("id") or "runtime")
    label = str(record.get("label") or runtime_id)
    target_type = str(record.get("target_type") or "local")
    if target_type == "cloud" or not record.get("available"):
        return f"{label} unavailable"
    auth = record.get("auth") if isinstance(record.get("auth"), dict) else {}
    message = str(auth.get("message") or "").strip()
    if message and not auth.get("logged_in"):
        return message
    if message and auth.get("logged_in"):
        return f"{label} unavailable"
    return f"{label} unavailable"


def _fallback_reply(*, composer_mode: str, user_prompt: str, context_block: str, reason: str) -> str:
    del user_prompt, context_block
    return (
        f"Lane B ({composer_mode}) cannot start because no CLI runtime is ready: {reason}. "
        "Open Runtime or `/vault`, then retry."
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


def _effective_cli_model(family: str, runtime_model: str) -> str:
    normalized = str(runtime_model or "").strip()
    if not normalized or normalized.lower() == "auto":
        env_key = "AXON_WATCH_CURSOR_MODEL" if family == "cursor" else "AXON_WATCH_CODEX_MODEL"
        normalized = str(os.environ.get(env_key, "")).strip()
    if normalized.lower() == "auto":
        return ""
    return normalized


def _ordered_candidates_for_dispatch(
    snapshot: dict[str, object],
    runtime_target: str | None,
) -> list[dict[str, object]]:
    candidates = ordered_runtime_candidates(snapshot)
    preferred = str(runtime_target or "").strip()
    if not preferred:
        return candidates
    by_id = {str(record.get("id") or ""): record for record in candidates}
    selected = by_id.get(preferred)
    if not selected:
        return candidates
    ordered = [selected]
    for record in candidates:
        runtime_id = str(record.get("id") or "")
        if runtime_id and runtime_id != preferred:
            ordered.append(record)
    return ordered


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

    for record in _ordered_candidates_for_dispatch(snapshot, runtime_target):
        runtime_id = str(record.get("id") or "")
        if not record.get("ready"):
            errors.append(_runtime_unready_reason(record))
            continue
        binary = str(record.get("binary") or "")
        family = str(record.get("family") or "")
        target_type = str(record.get("target_type") or "local")
        model = _effective_cli_model(family, str(runtime_model or ""))
        dispatch_env = subprocess_env
        if family == "cursor":
            dispatch_env = cursor_dispatch_env(
                subprocess_env,
                auth=record.get("auth") if isinstance(record.get("auth"), dict) else None,
            )
        try:
            if target_type == "cloud":
                raise RuntimeError(_cloud_runtime_message(record))
            if family == "cursor":
                cursor_reply = run_cursor_local(
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
                )
                content = _cursor_reply_content(cursor_reply, approval_notice)
                return _finish({
                    "content": content,
                    "dispatched": True,
                    "runtime_id": runtime_id,
                    "runtime_label": str(record.get("label") or runtime_id),
                    "reason": "",
                    "execution_tier": execution_tier,
                    "generated_image_paths": list(cursor_reply.generated_image_paths),
                })
            if family == "codex":
                content = run_codex_local(
                    binary=binary,
                    prompt=prompt,
                    workspace_root=workspace_root,
                    composer_mode=composer_mode,
                    execution_tier=execution_tier,
                    model=model,
                    subprocess_env=dispatch_env,
                    run_id=run_id,
                    on_chunk=on_chunk,
                )
                if approval_notice:
                    content = f"{content.rstrip()}\n\n---\n{approval_notice}"
                return _finish({
                    "content": content,
                    "dispatched": True,
                    "runtime_id": runtime_id,
                    "runtime_label": str(record.get("label") or runtime_id),
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
                    ),
                    "dispatched": False,
                    "runtime_id": runtime_id,
                    "runtime_label": str(record.get("label") or runtime_id),
                    "reason": str(exc),
                    "stopped": True,
                })
            detail = str(exc)
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
                            )
                            content = _cursor_reply_content(cursor_reply, approval_notice)
                        else:
                            content = run_codex_local(
                                binary=binary,
                                prompt=prompt,
                                workspace_root=workspace_root,
                                composer_mode=composer_mode,
                                execution_tier=execution_tier,
                                model=model,
                                subprocess_env=retry_env,
                                run_id=run_id,
                                on_chunk=on_chunk,
                            )
                        if approval_notice:
                            content = f"{content.rstrip()}\n\n---\n{approval_notice}"
                        payload = {
                            "content": content,
                            "dispatched": True,
                            "runtime_id": runtime_id,
                            "runtime_label": str(record.get("label") or runtime_id),
                            "reason": "",
                            "execution_tier": execution_tier,
                        }
                        if family == "cursor":
                            payload["generated_image_paths"] = list(cursor_reply.generated_image_paths)
                        return _finish(payload)
                    except RuntimeError as retry_exc:
                        detail = str(retry_exc)
            errors.append(
                summarize_auth_error(
                    family=family,
                    detail=detail,
                    had_api_key=env_has_api_key(dispatch_env, family=family),
                )
            )

    reason = "; ".join(item for item in errors if item) or "no CLI runtime is installed"
    return _finish({
        "content": _fallback_reply(
            composer_mode=composer_mode,
            user_prompt=user_prompt,
            context_block=context_block,
            reason=reason,
        ),
        "dispatched": False,
        "runtime_id": "",
        "runtime_label": "",
        "reason": reason,
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
