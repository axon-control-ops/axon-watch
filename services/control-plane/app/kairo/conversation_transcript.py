"""Voice transcript persistence for KAIRO conversation turns."""

from __future__ import annotations

import logging

from app.persistence.voice_transcript_store import append_voice_transcript

logger = logging.getLogger(__name__)


def log_voice_turn(
    *,
    session_id: str,
    workspace_id: str | None,
    raw_content: str,
    normalized_content: str,
    payload: dict[str, object],
    duration_ms: int | None = None,
    runtime_dispatched: bool = False,
) -> dict[str, object]:
    try:
        stt_note = None
        if raw_content.strip().lower() != normalized_content.strip().lower():
            stt_note = "stt_normalized"
        model_receipt = payload.get("model_receipt")
        receipt_dict = model_receipt if isinstance(model_receipt, dict) else None
        append_voice_transcript(
            session_id=session_id,
            workspace_id=workspace_id,
            raw_content=raw_content,
            normalized_content=normalized_content,
            reply=str(payload.get("reply") or ""),
            turn_kind=str(payload.get("turn_kind") or "unknown"),
            source=str(payload.get("source") or "unknown"),
            stt_note=stt_note,
            duration_ms=duration_ms,
            runtime_dispatched=runtime_dispatched,
            dispatch_lane=str(payload.get("dispatch_lane") or "") or None,
            action_tier=str(payload.get("action_tier") or "") or None,
            model_receipt=receipt_dict,
            voice_routing_mode=str(payload.get("voice_routing_mode") or "") or None,
        )
    except Exception as exc:
        logger.warning("voice transcript persistence failed: %s", exc)
    return payload
