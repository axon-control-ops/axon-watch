"""Workspace, handoff, terminal, and file routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, WebSocket

from app.chat.service import (
    ChatValidationError,
    create_workspace_chat_thread,
    get_workspace_chat_thread,
    list_workspace_chat_threads,
)
from app.routes.schemas import (
    CreateTerminalSessionRequest,
    CreateWorkspaceChatThreadRequest,
    CreateWorkspaceHandoffRequest,
    RegisterWorkspaceBindingRequest,
    RenameTerminalSessionRequest,
    RenameWorkspaceFileRequest,
    RouteTeammateRequest,
    WorkspaceComposerPrefsRequest,
    WriteWorkspaceFileRequest,
)
from app.terminal.session_handler import handle_terminal_session
from app.terminal.session_registry import (
    create_session,
    delete_session,
    ensure_operator_session,
    list_sessions,
    rename_session,
    serialize_session,
)
from app.terminal.session_runtime import terminate_runtime
from app.workspace_catalog import WorkspaceNotFoundError, get_workspace_record, list_workspace_records
from app.workspace_project_bindings import (
    WorkspaceBindingError,
    upsert_workspace_project_binding,
)
from app.workspace_files import (
    WorkspaceFileConflictError,
    WorkspaceFileError,
    list_workspace_files,
    read_workspace_file,
    read_workspace_file_bytes,
    rename_workspace_file,
    write_workspace_file,
)
from app.workspace_agents import (
    WorkspaceAgentError,
    get_company_roster,
    get_workspace_agent_record,
    list_role_catalog,
    list_workspace_agent_records,
)
from app.workspace_handoffs import (
    WorkspaceHandoffError,
    create_workspace_handoff,
    list_workspace_handoffs,
)

router = APIRouter()


@router.websocket("/api/workspaces/{workspace_id}/terminal")
async def workspace_terminal(
    websocket: WebSocket,
    workspace_id: str,
    session_id: str = Query("terminal-operator"),
    role: str = Query("operator"),
) -> None:
    await handle_terminal_session(
        websocket,
        workspace_id,
        session_id=session_id,
        role=role,
    )


@router.get("/api/workspaces")
def workspaces_index(scope: str = "") -> dict[str, Any]:
    operator_surface = scope.strip().lower() == "operator"
    items = list_workspace_records(operator_surface=operator_surface)
    return {"items": items, "count": len(items), "scope": "operator" if operator_surface else "all"}


@router.post("/api/workspaces")
def workspaces_register(body: RegisterWorkspaceBindingRequest) -> dict[str, Any]:
    try:
        binding = upsert_workspace_project_binding(
            workspace_id=body.workspace_id,
            project_root=body.project_root,
            display_name=body.display_name,
        )
        record = get_workspace_record(binding.workspace_id)
    except WorkspaceBindingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"workspace": record, "created": True}


@router.get("/api/workspaces/{workspace_id}")
def workspaces_show(workspace_id: str) -> dict[str, Any]:
    try:
        return get_workspace_record(workspace_id)
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/api/workspaces/{workspace_id}/composer-prefs")
def workspace_composer_prefs_get(workspace_id: str) -> dict[str, Any]:
    try:
        get_workspace_record(workspace_id)
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    from app.persistence.workspace_composer_prefs_store import get_workspace_composer_prefs

    prefs = get_workspace_composer_prefs(workspace_id)
    return {"workspace_id": workspace_id, **prefs}


@router.put("/api/workspaces/{workspace_id}/composer-prefs")
def workspace_composer_prefs_put(
    workspace_id: str,
    body: WorkspaceComposerPrefsRequest,
) -> dict[str, Any]:
    try:
        get_workspace_record(workspace_id)
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    from app.persistence.workspace_composer_prefs_store import set_workspace_composer_prefs

    prefs = set_workspace_composer_prefs(
        workspace_id,
        cursor_cli_model=body.cursor_cli_model,
        claude_cli_model=body.claude_cli_model,
        codex_cli_model=body.codex_cli_model,
        runtime_target=body.runtime_target,
        auto_allowed_runtimes=body.auto_allowed_runtimes,
        max_concurrent_runtimes=body.max_concurrent_runtimes,
    )
    return {"workspace_id": workspace_id, **prefs}


@router.get("/api/agents")
def agents_index(scope: str = "") -> dict[str, Any]:
    operator_surface = scope.strip().lower() == "operator"
    items = list_workspace_agent_records(operator_surface=operator_surface)
    return {"items": items, "count": len(items), "scope": "operator" if operator_surface else "all"}


@router.get("/api/workspaces/{workspace_id}/agent")
def workspace_agent_show(workspace_id: str) -> dict[str, object]:
    try:
        return get_workspace_agent_record(workspace_id)
    except WorkspaceAgentError as exc:
        status_code = 404 if "not found" in str(exc).lower() else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.get("/api/workspaces/{workspace_id}/company")
def workspace_company_show(workspace_id: str) -> dict[str, object]:
    try:
        return get_company_roster(workspace_id)
    except WorkspaceAgentError as exc:
        status_code = 404 if "not found" in str(exc).lower() else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.post("/api/workspaces/{workspace_id}/company/route-teammate")
def workspace_company_route_teammate(
    workspace_id: str,
    body: RouteTeammateRequest,
) -> dict[str, object]:
    from app.workspace_agents.teammate_route import (
        dispatch_model_tiebreak,
        route_teammate_decision,
    )

    prompt = body.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt must not be empty")
    try:
        decision = route_teammate_decision(
            workspace_id=workspace_id,
            prompt=prompt,
            current_employee_id=body.current_employee_id,
            use_model_tiebreak=body.use_model_tiebreak,
            dispatch_runtime=dispatch_model_tiebreak if body.use_model_tiebreak else None,
        )
    except WorkspaceAgentError as exc:
        status_code = 404 if "not found" in str(exc).lower() else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return decision.as_dict()


@router.get("/api/company-roles")
def company_roles_index() -> dict[str, object]:
    items = list_role_catalog()
    return {"items": items, "count": len(items)}


@router.post("/api/workspaces/{workspace_id}/handoffs")
def workspace_handoffs_create(
    workspace_id: str,
    body: CreateWorkspaceHandoffRequest,
) -> dict[str, object]:
    try:
        return create_workspace_handoff(
            source_workspace_id=workspace_id,
            target_workspace_id=body.target_workspace_id,
            task=body.task,
            reason=body.reason,
        )
    except WorkspaceHandoffError as exc:
        status_code = 404 if "not found" in str(exc).lower() else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.get("/api/workspaces/{workspace_id}/handoffs")
def workspace_handoffs_index(workspace_id: str) -> dict[str, object]:
    try:
        items = list_workspace_handoffs(workspace_id)
        return {"workspace_id": workspace_id, "items": items, "count": len(items)}
    except WorkspaceHandoffError as exc:
        status_code = 404 if "not found" in str(exc).lower() else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.get("/api/workspaces/{workspace_id}/chat/thread")
def workspace_chat_thread(workspace_id: str, surface: str = "operator") -> dict[str, object]:
    try:
        return get_workspace_chat_thread(workspace_id, thread_kind=surface)
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ChatValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/workspaces/{workspace_id}/chat/threads")
def workspace_chat_threads(
    workspace_id: str,
    surface: str = "ide",
    limit: int = 25,
) -> dict[str, object]:
    try:
        return list_workspace_chat_threads(
            workspace_id,
            thread_kind=surface,
            limit=limit,
        )
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ChatValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/workspaces/{workspace_id}/chat/threads")
def workspace_chat_threads_create(
    workspace_id: str,
    body: CreateWorkspaceChatThreadRequest,
) -> dict[str, object]:
    try:
        return create_workspace_chat_thread(
            workspace_id,
            thread_kind=body.surface,
            run_id=body.run_id,
            title=body.title,
            employee_id=body.employee_id,
            employee_role=body.employee_role,
        )
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ChatValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/workspaces/{workspace_id}/terminal/sessions")
def workspace_terminal_sessions(workspace_id: str) -> dict[str, object]:
    try:
        get_workspace_record(workspace_id)
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    ensure_operator_session(workspace_id)
    items = [serialize_session(record) for record in list_sessions(workspace_id)]
    return {"workspace_id": workspace_id, "items": items, "count": len(items)}


@router.post("/api/workspaces/{workspace_id}/terminal/sessions")
def workspace_terminal_sessions_create(
    workspace_id: str,
    body: CreateTerminalSessionRequest,
) -> dict[str, object]:
    try:
        get_workspace_record(workspace_id)
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    record = create_session(
        workspace_id=workspace_id,
        role=body.role,
        title=body.title,
        run_id=body.run_id,
        session_id=body.session_id,
    )
    return serialize_session(record)


@router.post("/api/workspaces/{workspace_id}/terminal/sessions/{session_id}/rename")
def workspace_terminal_sessions_rename(
    workspace_id: str,
    session_id: str,
    body: RenameTerminalSessionRequest,
) -> dict[str, object]:
    try:
        get_workspace_record(workspace_id)
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    updated = rename_session(workspace_id, session_id, body.title)
    if updated is None:
        raise HTTPException(status_code=404, detail="terminal session not found")
    return serialize_session(updated)


@router.delete("/api/workspaces/{workspace_id}/terminal/sessions/{session_id}")
def workspace_terminal_sessions_delete(workspace_id: str, session_id: str) -> dict[str, object]:
    try:
        get_workspace_record(workspace_id)
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    deleted = delete_session(workspace_id, session_id)
    terminate_runtime(workspace_id, session_id)
    if not deleted and session_id != "terminal-operator":
        raise HTTPException(status_code=404, detail="terminal session not found")
    ensure_operator_session(workspace_id)
    items = [serialize_session(record) for record in list_sessions(workspace_id)]
    return {"workspace_id": workspace_id, "deleted": deleted, "items": items, "count": len(items)}


@router.get("/api/workspaces/{workspace_id}/files")
def workspace_files_index(workspace_id: str) -> dict[str, object]:
    try:
        items = list_workspace_files(workspace_id)
        return {"workspace_id": workspace_id, "items": items, "count": len(items)}
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except WorkspaceFileError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/workspaces/{workspace_id}/files/{file_path:path}/raw")
def workspace_files_raw(workspace_id: str, file_path: str):
    try:
        payload, media_type, _ = read_workspace_file_bytes(workspace_id, file_path)
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except WorkspaceFileError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    from starlette.responses import Response

    return Response(
        content=payload,
        media_type=media_type,
        headers={"Cache-Control": "private, max-age=120"},
    )


@router.get("/api/workspaces/{workspace_id}/files/{file_path:path}")
def workspace_files_show(workspace_id: str, file_path: str) -> dict[str, object]:
    try:
        return read_workspace_file(workspace_id, file_path)
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except WorkspaceFileError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/api/workspaces/{workspace_id}/files/{file_path:path}")
def workspace_files_update(
    workspace_id: str,
    file_path: str,
    body: WriteWorkspaceFileRequest,
) -> dict[str, object]:
    try:
        return write_workspace_file(
            workspace_id, file_path, body.content, base_sha256=body.base_sha256
        )
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except WorkspaceFileConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except WorkspaceFileError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/workspaces/{workspace_id}/files/{file_path:path}/rename")
def workspace_files_rename(
    workspace_id: str,
    file_path: str,
    body: RenameWorkspaceFileRequest,
) -> dict[str, object]:
    try:
        return rename_workspace_file(workspace_id, file_path, body.new_path)
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except WorkspaceFileError as exc:
        status_code = 409 if "already exists" in str(exc) else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
