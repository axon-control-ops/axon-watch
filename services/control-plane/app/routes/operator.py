"""Operator briefing, presence, Kairo voice, and live event routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.kairo_conversation import converse_turn
from app.kairo_voice import generate_spoken_line, narration_allows_event
from app.live_event_hub import broadcast_live_event
from app.live_events import live_events_response
from app.operator_brain_graph import build_operator_brain_graph
from app.operator_briefing import build_operator_briefing
from app.operator_fleet_health import build_operator_fleet_health
from app.persistence import operator_presence_settings_store
from app.routes.schemas import (
    KairoConverseRequest,
    KairoSpeakRequest,
    KairoTtsRequest,
    OperatorPresenceSettingsRequest,
)

router = APIRouter()


@router.get("/api/briefing")
def operator_briefing(viewport_compact: bool = False, workspace_id: str = "") -> dict[str, object]:
    scoped_workspace_id = workspace_id.strip() or None
    return build_operator_briefing(
        viewport_compact=viewport_compact,
        workspace_id=scoped_workspace_id,
    )


@router.get("/api/operator/fleet-health")
def operator_fleet_health() -> dict[str, object]:
    return build_operator_fleet_health()


@router.get("/api/operator/brain-graph")
def operator_brain_graph() -> dict[str, object]:
    return build_operator_brain_graph()


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
    settings = operator_presence_settings_store.load_settings()
    narration = str(body.narration or settings.get("kairo_narration") or "minimal").strip().lower()
    if narration not in {"off", "minimal", "conversational"}:
        narration = "minimal"
    event_type = str(body.event_type or "").strip().lower()
    if not narration_allows_event(event_type, narration):  # type: ignore[arg-type]
        return {"line": "", "source": "skipped"}
    return generate_spoken_line(
        event_type=event_type,
        context=body.context,
        session_id=body.session_id,
        persona_enabled=bool(settings.get("operator_persona_enabled", True)),
        narration=narration,  # type: ignore[arg-type]
        workspace_id=body.workspace_id,
        use_runtime=body.use_runtime,
    )


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
    synthesized = synthesize_azure_speech(trimmed, voice=voice)
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
def kairo_voice_log(limit: int = Query(default=20, ge=1, le=100)) -> dict[str, object]:
    from app.persistence.voice_transcript_store import list_recent_voice_transcripts

    return {"entries": list_recent_voice_transcripts(limit=limit)}


@router.post("/api/kairo/converse")
def kairo_converse(body: KairoConverseRequest) -> dict[str, object]:
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
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/dev/trigger-spoken-briefing")
def dev_trigger_spoken_briefing() -> dict[str, object]:
    delivered = broadcast_live_event({"type": "spoken_briefing"})
    return {"ok": True, "subscribers": delivered}


@router.get("/api/live/events")
def live_events():
    return live_events_response()
