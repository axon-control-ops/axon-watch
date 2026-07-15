"""Operator briefing, presence, Kairo voice, and live event routes."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from app.kairo_conversation import converse_turn
from app.kairo_voice import generate_spoken_line, narration_allows_event
from app.live_event_hub import broadcast_live_event
from app.live_events import live_events_response
from app.operator_brain_graph import build_operator_brain_graph
from app.operator_briefing import build_operator_briefing
from app.operator_evidence import build_operator_evidence
from app.operator_fleet_health import build_operator_fleet_health
from app.persistence import operator_presence_settings_store
from app.persistence.operator_memory_store import create_memory, list_memories, search_memories
from app.research.service import fetch_url, search_web
from app.routes.schemas import (
    DebugSessionLogRequest,
    KairoConverseRequest,
    KairoSpeakRequest,
    KairoTtsRequest,
    OperatorMemoryCreateRequest,
    OperatorPresenceSettingsRequest,
    OperatorResearchCaptureRequest,
)

router = APIRouter()


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@router.get("/api/briefing")
def operator_briefing(
    viewport_compact: bool = False,
    workspace_id: str = "",
    light: bool = Query(False),
) -> dict[str, object]:
    scoped_workspace_id = workspace_id.strip() or None
    return build_operator_briefing(
        viewport_compact=viewport_compact,
        workspace_id=scoped_workspace_id,
        light=light,
    )


@router.get("/api/operator/fleet-health")
def operator_fleet_health() -> dict[str, object]:
    return build_operator_fleet_health()


@router.get("/api/operator/brain-graph")
def operator_brain_graph() -> dict[str, object]:
    return build_operator_brain_graph()


@router.get("/api/operator/evidence")
def operator_evidence(node_id: str) -> dict[str, object]:
    try:
        return build_operator_evidence(node_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/api/operator/memories")
def operator_memories(
    workspace_id: str = "",
    query: str = "",
    kind: str = "",
    limit: int = Query(default=12, ge=1, le=50),
) -> dict[str, object]:
    scoped_workspace_id = workspace_id.strip() or None
    if query.strip():
        items = search_memories(query, workspace_id=scoped_workspace_id, limit=limit)
    else:
        items = list_memories(
            workspace_id=scoped_workspace_id,
            kind=kind.strip() or None,
            limit=limit,
        )
    return {"items": items, "count": len(items)}


@router.post("/api/operator/memories")
def operator_memories_create(body: OperatorMemoryCreateRequest) -> dict[str, object]:
    trimmed_title = body.title.strip()
    trimmed_content = body.content.strip()
    if not trimmed_title or not trimmed_content:
        raise HTTPException(status_code=400, detail="title and content are required")
    record = create_memory(
        workspace_id=body.workspace_id.strip(),
        scope=body.scope.strip() or "workspace",
        kind=body.kind.strip() or "note",
        title=trimmed_title,
        content=trimmed_content,
        source_refs=body.source_refs,
        created_at=_utc_now(),
    )
    return {"item": record}


@router.post("/api/operator/research/capture")
def operator_research_capture(body: OperatorResearchCaptureRequest) -> dict[str, object]:
    query = (body.query or "").strip()
    url = (body.url or "").strip()
    if not query and not url:
        raise HTTPException(status_code=400, detail="query or url is required")

    result = search_web(query) if query else fetch_url(url)
    title = body.title.strip() or query or url
    source_refs = list(body.source_refs)
    receipt = result.get("receipt")
    if isinstance(receipt, dict):
        source_refs.append(
            {
                "ref_type": "research_receipt",
                "ref_id": str(receipt.get("target") or title),
                "label": str(receipt.get("provider") or "research"),
                "workspace_id": body.workspace_id.strip(),
            }
        )
    memory = create_memory(
        workspace_id=body.workspace_id.strip(),
        scope="workspace" if body.workspace_id.strip() else "personal",
        kind="research",
        title=title,
        content=str(result.get("summary") or result.get("content") or result.get("error") or "").strip()
        or title,
        source_refs=source_refs,
        created_at=_utc_now(),
    )
    return {"result": result, "memory": memory}


@router.get("/api/operator-presence/settings")
def operator_presence_settings_get() -> dict[str, object]:
    settings = operator_presence_settings_store.load_settings()
    return {"settings": settings}


@router.put("/api/operator-presence/settings")
def operator_presence_settings_put(body: OperatorPresenceSettingsRequest) -> dict[str, object]:
    current = operator_presence_settings_store.load_settings()
    patch = body.model_dump(exclude_none=True)
    current.update(patch)
    return operator_presence_settings_store.save_settings(current)


@router.post("/api/kairo/speak")
def kairo_speak(body: KairoSpeakRequest) -> dict[str, str]:
    from app.persistence.voice_transcript_store import append_voice_transcript

    settings = operator_presence_settings_store.load_settings()
    narration = str(body.narration or settings.get("kairo_narration") or "minimal").strip().lower()
    if narration not in {"off", "minimal", "conversational"}:
        narration = "minimal"
    event_type = str(body.event_type or "").strip().lower()
    if not narration_allows_event(event_type, narration):  # type: ignore[arg-type]
        return {"line": "", "source": "skipped"}
    payload = generate_spoken_line(
        event_type=event_type,
        context=body.context,
        session_id=body.session_id,
        persona_enabled=bool(settings.get("operator_persona_enabled", True)),
        narration=narration,  # type: ignore[arg-type]
        workspace_id=body.workspace_id,
        use_runtime=body.use_runtime,
    )
    line = str(payload.get("line") or "").strip()
    if line:
        raw_content = (
            str((body.context or {}).get("operator_prompt") or "").strip()
            or str((body.context or {}).get("literal_line") or "").strip()
            or event_type
        )
        append_voice_transcript(
            session_id=body.session_id,
            workspace_id=body.workspace_id or None,
            raw_content=raw_content,
            normalized_content=raw_content,
            reply=line,
            turn_kind=event_type or "spoken_line",
            source=str(payload.get("source") or "unknown"),
            runtime_dispatched=str(payload.get("source") or "") == "model",
        )
    return payload


@router.post("/api/kairo/tts")
def kairo_tts(body: KairoTtsRequest) -> dict[str, object]:
    import base64

    from app.azure_tts import (
        DEFAULT_AZURE_VOICE,
        azure_speech_configured,
        synthesize_azure_speech,
    )
    from app.cli_runtime.vault_keys import runtime_vault_posture

    trimmed = body.text.strip()
    if not trimmed:
        raise HTTPException(status_code=400, detail="text must not be empty")

    if not azure_speech_configured():
        posture = runtime_vault_posture()
        reason = "vault_locked" if not posture.get("unlocked") else "missing_key"
        return {
            "available": False,
            "provider": "browser",
            "reason": reason,
        }

    voice = str(body.voice or DEFAULT_AZURE_VOICE).strip() or DEFAULT_AZURE_VOICE
    synthesized = synthesize_azure_speech(
        trimmed, voice=voice, rate=body.rate, pitch=body.pitch
    )
    if not synthesized:
        return {
            "available": False,
            "provider": "browser",
            "reason": "synthesis_failed",
        }

    audio, content_type = synthesized
    return {
        "available": True,
        "provider": "azure",
        "voice": voice,
        "content_type": content_type,
        "audio_base64": base64.b64encode(audio).decode("ascii"),
    }


@router.get("/api/kairo/voice-log")
def kairo_voice_log(
    limit: int = Query(default=20, ge=1, le=100),
    session_id: str = Query(default=""),
) -> dict[str, object]:
    from app.persistence.voice_transcript_store import list_recent_voice_transcripts

    effective_limit = 5 if session_id.strip() and limit == 20 else limit
    return {
        "entries": list_recent_voice_transcripts(
            limit=effective_limit,
            session_id=session_id or None,
        )
    }


@router.post("/api/kairo/converse")
def kairo_converse(
    body: KairoConverseRequest,
    refresh: bool = Query(default=False),
) -> dict[str, object]:
    trimmed = body.content.strip()
    if not trimmed:
        raise HTTPException(status_code=400, detail="content must not be empty")
    try:
        return converse_turn(
            content=trimmed,
            session_id=body.session_id,
            workspace_id=body.workspace_id or None,
            use_runtime=body.use_runtime,
            answer_tier=body.answer_tier,
            context_workspace_id=body.context_workspace_id or None,
            context_signal_id=body.context_signal_id or None,
            context_node_id=body.context_node_id or None,
            force_refresh=refresh,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/dev/trigger-spoken-briefing")
def dev_trigger_spoken_briefing() -> dict[str, object]:
    delivered = broadcast_live_event({"type": "spoken_briefing"})
    return {"ok": True, "subscribers": delivered}


@router.post("/api/dev/debug-session-log")
def dev_debug_session_log(body: DebugSessionLogRequest) -> dict[str, object]:
    """Append one NDJSON evidence line for Debug-mode instrumentation."""
    import json
    from pathlib import Path

    from app.terminal.workspace_roots import WorkspaceRootError, resolve_workspace_root

    workspace_root: Path | None = None
    workspace_id = (body.workspace_id or "").strip() or "workspace_axon_watch"
    try:
        workspace_root = resolve_workspace_root(workspace_id)
    except WorkspaceRootError:
        workspace_root = None
    if workspace_root is None:
        workspace_root = Path(__file__).resolve().parents[4]

    axon_dir = workspace_root / ".axon"
    axon_dir.mkdir(parents=True, exist_ok=True)
    log_path = axon_dir / "debug-session.ndjson"
    payload = {
        "hypothesisId": body.hypothesisId,
        "location": body.location,
        "message": body.message,
        "data": body.data or {},
        "timestamp": body.timestamp if body.timestamp is not None else __import__("time").time() * 1000,
    }
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True) + "\n")
    return {"ok": True, "path": str(log_path)}


@router.get("/api/live/events")
def live_events():
    return live_events_response()
