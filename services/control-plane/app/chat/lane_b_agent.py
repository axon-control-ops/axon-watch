"""Lane B context helpers and runtime-backed reply routing for IDE composer modes."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from app.cli_runtime.router import dispatch_ide_composer
from app.terminal.workspace_roots import WorkspaceRootError, resolve_workspace_root
from app.workspace_files import WorkspaceFileError, list_workspace_files


@dataclass(frozen=True)
class LaneBContext:
    workspace_id: str
    composer_mode: str
    active_file_path: str | None = None


def _read_file_preview(workspace_id: str, path: str, *, max_chars: int = 1200) -> str:
    from app.workspace_files import read_workspace_file

    try:
        payload = read_workspace_file(workspace_id, path)
        content = str(payload.get("content", ""))
        if len(content) <= max_chars:
            return content
        return f"{content[: max_chars - 3].rstrip()}..."
    except (WorkspaceFileError, OSError):
        return ""


def build_lane_b_context_block(context: LaneBContext) -> str:
    lines = [
        f"Workspace: {context.workspace_id}",
        f"Composer mode: {context.composer_mode}",
    ]
    try:
        root = resolve_workspace_root(context.workspace_id)
        lines.append(f"Project root: {root}")
    except WorkspaceRootError as exc:
        lines.append(f"Project root unavailable: {exc}")

    if context.active_file_path:
        preview = _read_file_preview(context.workspace_id, context.active_file_path)
        lines.append(f"Active file: {context.active_file_path}")
        if preview:
            lines.append(f"Active file preview:\n{preview}")

    try:
        files = list_workspace_files(context.workspace_id)
        if files:
            sample = ", ".join(item["path"] for item in files[:12])
            lines.append(f"Workspace files (sample): {sample}")
    except (WorkspaceFileError, OSError):
        pass

    return "\n".join(lines)


def _fallback_reply(*, context: LaneBContext, user_prompt: str, reason: str) -> str:
    context_block = build_lane_b_context_block(context)
    return (
        f"Lane B ({context.composer_mode}) is active, but the CLI runtime fabric is "
        f"unavailable ({reason}).\n\n"
        f"Operator request:\n{user_prompt.strip()}\n\n"
        f"Workspace context:\n```\n{context_block}\n```\n\n"
        "Sign in to Cursor or Codex locally, then use the runtime status route "
        "(`/api/runtime/status`) to inspect readiness. Operator commands (`git status`, "
        "`run …`) still work in Command mode."
    )


def generate_lane_b_result(
    *,
    context: LaneBContext,
    user_prompt: str,
    run_id: str = "",
    runtime_target: str | None = None,
    runtime_model: str | None = None,
    execution_access: str | None = None,
    on_chunk: Callable[[str, str], None] | None = None,
) -> dict[str, object]:
    trimmed = user_prompt.strip()
    if not trimmed:
        return {
            "content": "Send a prompt to start Lane B conversation.",
            "dispatched": False,
            "runtime_id": "",
            "runtime_label": "",
            "reason": "empty prompt",
        }

    context_block = build_lane_b_context_block(context)
    try:
        return dispatch_ide_composer(
            workspace_id=context.workspace_id,
            composer_mode=context.composer_mode,
            user_prompt=trimmed,
            context_block=context_block,
            run_id=run_id,
            runtime_target=runtime_target,
            runtime_model=runtime_model,
            execution_access=execution_access,
            on_chunk=on_chunk,
        )
    except RuntimeError as exc:
        return {
            "content": _fallback_reply(context=context, user_prompt=trimmed, reason=str(exc)),
            "dispatched": False,
            "runtime_id": "",
            "runtime_label": "",
            "reason": str(exc),
        }


def generate_lane_b_reply(*, context: LaneBContext, user_prompt: str) -> str:
    return str(generate_lane_b_result(context=context, user_prompt=user_prompt).get("content") or "")


def is_lane_b_composer_mode(composer_mode: str | None) -> bool:
    normalized = str(composer_mode or "command").strip().lower()
    return normalized in {"ask", "agent", "plan"}


def should_use_lane_b(*, composer_mode: str | None, command_intent: str) -> bool:
    # IDE composer modes always stay on Lane B. Command-intent keyword matches
    # (e.g. a prompt mentioning "readme" or "git status") must never hijack an
    # IDE turn into the operator command lane/thread.
    del command_intent
    return is_lane_b_composer_mode(composer_mode)
