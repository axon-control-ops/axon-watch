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
from app.cli_runtime.recovery import ordered_runtime_candidates
from app.cli_runtime.subprocess_runner import RuntimeProcessStoppedError
from app.cli_runtime.cursor_agent import run_cursor_local
from app.cli_runtime.runtime_auth import (
    env_has_api_key,
    env_without_api_keys,
    looks_like_auth_error,
    prefer_subscription_over_process_api_key,
    summarize_auth_error,
)
from app.cli_runtime.vault_keys import runtime_subprocess_env
from app.runs.service import RunNotFoundError, get_run
from app.terminal.workspace_roots import WorkspaceRootError, resolve_workspace_root


def _system_prompt(composer_mode: str, execution_tier: str = "consultative") -> str:
    if composer_mode == "ask":
        return (
            "You are Axon-X Lane B in Ask mode. Stay read-only. Answer using the supplied "
            "workspace context and do not claim you edited files or ran commands."
        )
    if composer_mode == "plan":
        return (
            "You are Axon-X Lane B in Plan mode. Produce a short numbered plan using the "
            "supplied workspace context. Do not claim execution happened."
        )
    if execution_tier == "executing":
        return (
            "You are Axon-X Lane B in Agent mode with Full Access. The operator has "
            "consented to tool execution: edit files and run commands inside the "
            "Project root shown in workspace context as needed to complete the request "
            "now. Use workspace-relative paths such as README.md — never edit Cursor "
            "metadata directories. Do the work first, then reply with a short summary "
            "of what changed."
        )
    return (
        "You are Axon-X Lane B in Agent mode (consultative slice). Answer using the "
        "supplied workspace context, propose concrete next steps, and do not claim you "
        "edited files or ran commands."
    )


def _build_prompt(
    *,
    composer_mode: str,
    user_prompt: str,
    context_block: str,
    execution_tier: str = "consultative",
) -> str:
    return (
        f"{_system_prompt(composer_mode, execution_tier)}\n\n"
        f"Workspace context:\n{context_block}\n\n"
        f"Operator request:\n{user_prompt.strip()}"
    )


def _fallback_reply(*, composer_mode: str, user_prompt: str, context_block: str, reason: str) -> str:
    return (
        f"Lane B ({composer_mode}) is active, but no approved CLI runtime is ready ({reason}).\n\n"
        f"Operator request:\n{user_prompt.strip()}\n\n"
        f"Workspace context:\n```\n{context_block}\n```\n\n"
        "Open `/vault` to unlock provider keys, then refresh runtime status. You can also sign in to "
        "Cursor or Codex locally. Axon-X treats Cursor as the primary interactive runtime "
        "and Codex as the scripted/runtime fallback."
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
) -> dict[str, object]:
    snapshot = runtime_status_snapshot()
    workspace_root = _resolve_workspace_root(workspace_id)
    if workspace_root is None:
        return {
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
        }

    run_phase = _run_phase(run_id)
    execution_tier = resolve_runtime_execution_tier(
        composer_mode=composer_mode,
        run_phase=run_phase,
        execution_access=execution_access,
    )
    prompt = _build_prompt(
        composer_mode=composer_mode,
        user_prompt=user_prompt,
        context_block=context_block,
        execution_tier=execution_tier,
    )
    approval_notice = consultative_only_notice(
        composer_mode=composer_mode,
        run_phase=run_phase,
        execution_access=execution_access,
    )
    errors: list[str] = []
    subprocess_env = runtime_subprocess_env()
    if prefer_subscription_over_process_api_key() and subprocess_env.get("CURSOR_API_KEY"):
        subprocess_env = env_without_api_keys(subprocess_env, family="cursor")

    for record in _ordered_candidates_for_dispatch(snapshot, runtime_target):
        runtime_id = str(record.get("id") or "")
        if not record.get("ready"):
            errors.append(str(record.get("auth", {}).get("message") or f"{runtime_id} unavailable"))
            continue
        binary = str(record.get("binary") or "")
        family = str(record.get("family") or "")
        target_type = str(record.get("target_type") or "local")
        model = _effective_cli_model(family, str(runtime_model or ""))
        dispatch_env = subprocess_env
        auth_method = str((record.get("auth") or {}).get("auth_method") or "")
        if family == "cursor" and auth_method == "oauth":
            dispatch_env = env_without_api_keys(subprocess_env, family="cursor")
        try:
            if target_type == "cloud":
                raise RuntimeError(_cloud_runtime_message(record))
            if family == "cursor":
                content = run_cursor_local(
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
                return {
                    "content": content,
                    "dispatched": True,
                    "runtime_id": runtime_id,
                    "runtime_label": str(record.get("label") or runtime_id),
                    "reason": "",
                    "execution_tier": execution_tier,
                }
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
                return {
                    "content": content,
                    "dispatched": True,
                    "runtime_id": runtime_id,
                    "runtime_label": str(record.get("label") or runtime_id),
                    "reason": "",
                    "execution_tier": execution_tier,
                }
        except RuntimeError as exc:
            if isinstance(exc, RuntimeProcessStoppedError):
                return {
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
                }
            detail = str(exc)
            if looks_like_auth_error(detail) and env_has_api_key(dispatch_env, family=family):
                retry_env = env_without_api_keys(dispatch_env, family=family)
                if retry_env != dispatch_env:
                    try:
                        if family == "cursor":
                            content = run_cursor_local(
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
                        return {
                            "content": content,
                            "dispatched": True,
                            "runtime_id": runtime_id,
                            "runtime_label": str(record.get("label") or runtime_id),
                            "reason": "",
                            "execution_tier": execution_tier,
                        }
                    except RuntimeError as retry_exc:
                        detail = str(retry_exc)
            errors.append(summarize_auth_error(family=family, detail=detail))

    reason = "; ".join(item for item in errors if item) or "no CLI runtime is installed"
    return {
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
    }


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
