"""Pydantic request models for control-plane HTTP routes."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel


class WriteWorkspaceFileRequest(BaseModel):
    content: str


class WorkspaceComposerPrefsRequest(BaseModel):
    cursor_cli_model: str | None = None


class RenameWorkspaceFileRequest(BaseModel):
    new_path: str


class CreateRunRequest(BaseModel):
    workspace_id: str
    mode: str = "agent"
    summary: str
    detail: str = ""
    requires_approval: bool = False
    employee_role: str | None = None


class EditorSelectionContextRequest(BaseModel):
    file_path: str
    start_line: int
    end_line: int
    text: str


class PostChatMessageRequest(BaseModel):
    workspace_id: str
    content: str
    thread_id: str | None = None
    run_id: str | None = None
    composer_mode: str | None = None
    active_file_path: str | None = None
    editor_selection: EditorSelectionContextRequest | None = None
    terminal_snippet: str | None = None
    attachment_ids: list[str] | None = None
    runtime_target: str | None = None
    runtime_model: str | None = None
    execution_access: str | None = None
    kairo_session_id: str | None = None


class CreateWorkspaceChatThreadRequest(BaseModel):
    surface: str = "ide"
    run_id: str | None = None
    title: str | None = None
    employee_id: str | None = None
    employee_role: str | None = None


class CreateTerminalSessionRequest(BaseModel):
    role: str = "operator"
    title: str | None = None
    run_id: str | None = None
    session_id: str | None = None


class EnqueueAgentTerminalJobRequest(BaseModel):
    command: str
    run_id: str | None = None
    stream_to_chat: bool | None = None
    thread_id: str | None = None
    message_id: str | None = None


class RenameTerminalSessionRequest(BaseModel):
    title: str


class CreateWorkspaceHandoffRequest(BaseModel):
    target_workspace_id: str
    task: str
    reason: str = ""


class RouteTeammateRequest(BaseModel):
    prompt: str
    current_employee_id: str | None = None
    use_model_tiebreak: bool = True


class RegisterWorkspaceBindingRequest(BaseModel):
    workspace_id: str
    project_root: str
    display_name: str | None = None


class WatchCommandRequest(BaseModel):
    command_id: str | None = None
    command_type: str
    target_type: str = ""
    target_id: str = ""
    requested_by: str = "operator"
    payload: dict[str, object] | None = None
    requested_at: str | None = None


class AcknowledgeInboxSignalsRequest(BaseModel):
    signal_ids: list[str]


class SentryResolveRequest(BaseModel):
    status: str = "resolved"
    requested_by: str = "operator"


class SentryAttendRequest(BaseModel):
    confirm_release: str = ""
    requested_by: str = "operator"
    mark_resolved_in_next_release: bool = True
    workspace_id: str = "workspace_dashpro"


class VaultImportRequest(BaseModel):
    secrets: dict[str, str] = {}
    export_text: str = ""


class VaultSetupRequest(BaseModel):
    master_password: str


class VaultUnlockRequest(BaseModel):
    master_password: str
    totp_code: str
    remember_me: bool = False


class VaultSecretRequest(BaseModel):
    name: str
    category: str = "general"
    username: str = ""
    password: str = ""
    url: str = ""
    notes: str = ""


class VaultExportRequest(BaseModel):
    backup_password: str


class OperatorPresenceSettingsRequest(BaseModel):
    operator_persona_enabled: bool | None = None
    spoken_alerts_enabled: bool | None = None
    privacy_mode: bool | None = None
    mobile_compact_preferred: bool | None = None
    kairo_narration: str | None = None
    ide_voice_strip_enabled: bool | None = None
    hands_free_enabled: bool | None = None
    proactive_duplex_enabled: bool | None = None
    autonomy_mode: str | None = None
    speech_rate: float | None = None
    speech_pitch: float | None = None
    azure_voice_id: str | None = None
    stt_mode: str | None = None
    voice_routing_mode: str | None = None
    vaxon_model_id: str | None = None
    narrate_tool_progress: bool | None = None


class KairoSpeakRequest(BaseModel):
    event_type: str
    context: dict[str, Any] = {}
    session_id: str = "default"
    workspace_id: str = ""
    use_runtime: bool = True
    narration: str | None = None


class KairoConverseRequest(BaseModel):
    content: str
    session_id: str = "default"
    workspace_id: str = ""
    use_runtime: bool = False
    answer_tier: str = "fast"
    context_workspace_id: str = ""
    context_signal_id: str = ""
    context_node_id: str = ""
    attachment_ids: list[str] | None = None
    # Secure default for current and stale clients: text is an Ask unless the
    # client deliberately declares the Dispatch action.
    submission_intent: Literal["ask", "dispatch"] = "ask"


class KairoTtsRequest(BaseModel):
    text: str
    voice: str | None = None
    rate: float | None = None
    pitch: float | None = None
    # Mid-utterance chunks skip the long sink wake-up silence.
    continuation: bool | None = None


class DebugSessionLogRequest(BaseModel):
    hypothesisId: str
    location: str
    message: str
    data: dict[str, Any] = {}
    timestamp: float | int | None = None
    workspace_id: str = ""


class OperatorMemoryCreateRequest(BaseModel):
    workspace_id: str = ""
    scope: str = "workspace"
    kind: str = "note"
    title: str
    content: str
    source_refs: list[dict[str, Any]] = []


class OperatorResearchCaptureRequest(BaseModel):
    workspace_id: str = ""
    title: str = ""
    query: str | None = None
    url: str | None = None
    source_refs: list[dict[str, Any]] = []
