"""Operator briefing, presence, Kairo voice, and live event routes."""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

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
    if "autonomy_mode" in patch:
        mode = str(patch.get("autonomy_mode") or "manual").strip().lower()
        if mode not in {"manual", "semi", "full"}:
            patch.pop("autonomy_mode", None)
        else:
            patch["autonomy_mode"] = mode
            # Full autonomy drives continuous worker starts; manual/semi keep them paused.
            from app.persistence import worker_scheduler_settings_store

            worker_scheduler_settings_store.patch_settings(
                {"scheduler_enabled": mode == "full"}
            )
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
        leading_audio_guard_ms,
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
        "leading_audio_guard_ms": leading_audio_guard_ms(trimmed),
    }


@router.get("/api/kairo/stt")
def kairo_stt_status() -> dict[str, object]:
    from app.azure_stt import stt_availability_payload

    return stt_availability_payload()


@router.post("/api/kairo/stt")
async def kairo_stt_transcribe(
    file: UploadFile = File(...),
    language: str = Query(default="en-US"),
) -> dict[str, object]:
    from app.azure_stt import (
        MAX_STT_UPLOAD_BYTES,
        transcribe_azure_stt,
    )

    settings = operator_presence_settings_store.load_settings()
    if bool(settings.get("privacy_mode")):
        return {
            "available": False,
            "transcript": "",
            "provider": "browser",
            "confidence": None,
            "reason": "privacy_mode",
        }

    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="audio payload must not be empty")
    if len(raw_bytes) > MAX_STT_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"audio exceeds {MAX_STT_UPLOAD_BYTES} byte limit",
        )

    filename = str(file.filename or "capture.ogg")
    mime_type = str(file.content_type or "application/octet-stream")
    try:
        result = transcribe_azure_stt(
            raw_bytes,
            filename=filename,
            mime_type=mime_type,
            language=language,
        )
    except ValueError as exc:
        reason = str(exc)
        return {
            "available": False,
            "transcript": "",
            "provider": "browser",
            "confidence": None,
            "reason": reason,
        }

    if result is None:
        return {
            "available": False,
            "transcript": "",
            "provider": "browser",
            "confidence": None,
            "reason": "cloud_stt_unavailable",
        }

    return {
        "available": True,
        "transcript": result.transcript,
        "provider": result.provider,
        "confidence": result.confidence,
        "reason": None,
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
    attachment_ids = list(body.attachment_ids or [])
    if not trimmed and not attachment_ids:
        raise HTTPException(status_code=400, detail="content must not be empty")
    try:
        return converse_turn(
            content=trimmed or "Please review the attached files.",
            session_id=body.session_id,
            workspace_id=body.workspace_id or None,
            use_runtime=body.use_runtime or bool(attachment_ids),
            answer_tier="deep" if attachment_ids else body.answer_tier,
            context_workspace_id=body.context_workspace_id or None,
            context_signal_id=body.context_signal_id or None,
            context_node_id=body.context_node_id or None,
            force_refresh=refresh,
            attachment_ids=attachment_ids,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/dev/trigger-spoken-briefing")
def dev_trigger_spoken_briefing() -> dict[str, object]:
    delivered = broadcast_live_event({"type": "spoken_briefing"})
    return {"ok": True, "subscribers": delivered}


@router.get("/api/dev/debug-session-log")
def dev_debug_session_log_read(
    workspace_id: str = "",
    limit: int = 80,
) -> dict[str, object]:
    """Read recent Debug Mode NDJSON lines for the IDE thread log panel."""
    from app.debug_session_log import (
        read_debug_session_log_lines,
        resolve_debug_session_log_path,
    )

    path = resolve_debug_session_log_path(workspace_id)
    entries = read_debug_session_log_lines(workspace_id=workspace_id, limit=limit)
    return {
        "ok": True,
        "path": str(path),
        "count": len(entries),
        "entries": entries,
    }


@router.post("/api/dev/debug-session-log")
def dev_debug_session_log(body: DebugSessionLogRequest) -> dict[str, object]:
    """Append one NDJSON evidence line for Debug-mode instrumentation."""
    if os.environ.get("AXON_DEBUG_SESSION_LOG") != "1":
        raise HTTPException(status_code=404, detail="Not found")

    import json
    import time

    from app.debug_session_log import resolve_debug_session_log_path

    log_path = resolve_debug_session_log_path(body.workspace_id)
    payload = {
        "hypothesisId": body.hypothesisId,
        "location": body.location,
        "message": body.message,
        "data": body.data or {},
        "timestamp": body.timestamp if body.timestamp is not None else time.time() * 1000,
    }
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True) + "\n")
    return {"ok": True, "path": str(log_path)}


@router.get("/api/operator/autonomy/status")
def operator_autonomy_status(workspace_id: str = "") -> dict[str, object]:
    """Read-only Mission Control autonomy feed (mode, scheduler, receipts)."""
    from app.workspace_agents.autonomous_attention import build_autonomy_status_feed

    return build_autonomy_status_feed(workspace_id=workspace_id.strip() or None)


@router.post("/api/operator/autonomy/scan")
def operator_autonomy_scan() -> dict[str, object]:
    """Operator-triggered attend scan (also runs on Full-autonomy scheduler ticks)."""
    from app.persistence import operator_presence_settings_store
    from app.workspace_agents.autonomous_attention import run_autonomous_attention_scan

    settings = operator_presence_settings_store.load_settings()
    mode = str(settings.get("autonomy_mode") or "manual").strip().lower()
    if mode != "full":
        raise HTTPException(
            status_code=400,
            detail=f"attend scan requires autonomy_mode=full (current={mode})",
        )
    return run_autonomous_attention_scan(include_lead_checkin=False)


@router.post("/api/operator/autonomy/decisions/{receipt_id}")
def operator_autonomy_decision_resolve(
    receipt_id: str,
    body: dict[str, object],
) -> dict[str, object]:
    """Resolve one exact critical/dangerous decision as approve or reject."""
    from app.workspace_agents.autonomous_attention import resolve_autonomy_decision

    resolution = str(body.get("resolution") or "").strip().lower()
    try:
        return resolve_autonomy_decision(receipt_id, resolution=resolution)
    except ValueError as exc:
        detail = str(exc)
        status_code = 404 if "not found" in detail else 400
        raise HTTPException(status_code=status_code, detail=detail) from exc


@router.get("/api/live/events")
def live_events():
    return live_events_response()
