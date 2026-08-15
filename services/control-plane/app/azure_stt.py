"""Bounded Azure Speech STT for KAIRO cloud capture (REST v1 short audio)."""

from __future__ import annotations

import http.client
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

from app.azure_tts import resolve_azure_speech_credentials, resolve_azure_speech_region
from app.operator_persona_stt_aliases import normalize_persona_stt_aliases

MAX_STT_UPLOAD_BYTES = 2 * 1024 * 1024
STT_REQUEST_TIMEOUT_SECONDS = 12
DEFAULT_STT_LANGUAGE = "en-US"
STT_READ_ATTEMPTS = 2
STT_RETRY_BACKOFF_SECONDS = 0.15

_AZURE_OGG_CONTENT_TYPE = "audio/ogg; codecs=opus"
_AZURE_WAV_CONTENT_TYPE = "audio/wav; codecs=audio/pcm; samplerate=16000"


@dataclass(frozen=True)
class AzureSttResult:
    transcript: str
    confidence: float | None
    provider: str = "azure"


def azure_stt_configured() -> bool:
    key, _region = resolve_azure_speech_credentials()
    return bool(key)


def resolve_stt_language(language: str | None) -> str:
    raw = str(language or "").strip()
    if not raw:
        return DEFAULT_STT_LANGUAGE
    if re.fullmatch(r"[a-z]{2}(?:-[A-Z]{2})?", raw):
        return raw
    return DEFAULT_STT_LANGUAGE


def _azure_content_type(filename: str, mime_type: str) -> str | None:
    lowered_name = str(filename or "").strip().lower()
    lowered_mime = str(mime_type or "").strip().lower()
    if lowered_name.endswith(".wav") or "audio/wav" in lowered_mime:
        return _AZURE_WAV_CONTENT_TYPE
    if lowered_name.endswith(".ogg") or "audio/ogg" in lowered_mime:
        return _AZURE_OGG_CONTENT_TYPE
    if "webm" in lowered_mime or lowered_name.endswith(".webm"):
        return None
    if lowered_mime.startswith("audio/"):
        return _AZURE_OGG_CONTENT_TYPE
    return None


def _parse_confidence(payload: dict[str, object]) -> float | None:
    nbest = payload.get("NBest")
    if not isinstance(nbest, list) or not nbest:
        return None
    first = nbest[0]
    if not isinstance(first, dict):
        return None
    raw = first.get("Confidence")
    if isinstance(raw, (int, float)):
        return float(raw)
    return None


def _parse_transcript(payload: dict[str, object]) -> str:
    nbest = payload.get("NBest")
    if isinstance(nbest, list) and nbest:
        first = nbest[0]
        if isinstance(first, dict):
            display = str(first.get("Display") or first.get("Lexical") or "").strip()
            if display:
                return display
    return str(payload.get("DisplayText") or "").strip()


def transcribe_azure_stt(
    audio_bytes: bytes,
    *,
    filename: str = "capture.ogg",
    mime_type: str = "audio/ogg",
    language: str | None = None,
) -> AzureSttResult | None:
    if not audio_bytes:
        return None
    if len(audio_bytes) > MAX_STT_UPLOAD_BYTES:
        raise ValueError("audio_too_large")

    content_type = _azure_content_type(filename, mime_type)
    if not content_type:
        raise ValueError("unsupported_audio_format")

    speech_key, speech_region = resolve_azure_speech_credentials()
    if not speech_key:
        return None

    resolved_language = resolve_stt_language(language)
    query = urllib.parse.urlencode(
        {"language": resolved_language, "format": "detailed"},
    )
    region = resolve_azure_speech_region(speech_region)
    url = (
        f"https://{region}.stt.speech.microsoft.com/"
        f"speech/recognition/conversation/cognitiveservices/v1?{query}"
    )
    request = urllib.request.Request(
        url,
        data=audio_bytes,
        headers={
            "Ocp-Apim-Subscription-Key": speech_key,
            "Content-Type": content_type,
            "Accept": "application/json",
            "User-Agent": "axon-watch-control-plane",
        },
        method="POST",
    )

    # Azure occasionally drops the connection mid-response (RemoteDisconnected /
    # IncompleteRead) — those are http.client.HTTPException subclasses that
    # urllib does NOT wrap into URLError, so they used to escape this call
    # entirely and surface as an unhandled 500 (see azure_tts.py's matching
    # fix for the same Azure Speech quirk on the TTS side). Retry quietly once,
    # then fall back to the caller's existing None → browser-STT contract.
    body: str | None = None
    for attempt in range(STT_READ_ATTEMPTS):
        try:
            with urllib.request.urlopen(request, timeout=STT_REQUEST_TIMEOUT_SECONDS) as response:
                body = response.read().decode("utf-8", errors="replace")
            break
        except http.client.HTTPException:
            if attempt + 1 < STT_READ_ATTEMPTS:
                time.sleep(STT_RETRY_BACKOFF_SECONDS * (attempt + 1))
                continue
            return None
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            return None
    if body is None:
        return None

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None

    status = str(payload.get("RecognitionStatus") or "").strip()
    if status == "NoMatch":
        return AzureSttResult(transcript="", confidence=None)
    if status != "Success":
        return None

    transcript = normalize_persona_stt_aliases(_parse_transcript(payload))
    return AzureSttResult(
        transcript=transcript,
        confidence=_parse_confidence(payload),
    )


def stt_availability_payload() -> dict[str, object]:
    configured = azure_stt_configured()
    return {
        "available": configured,
        "provider": "azure" if configured else "none",
        "reason": None if configured else "azure_speech_not_configured",
        "max_upload_bytes": MAX_STT_UPLOAD_BYTES,
        "supported_mime_types": ["audio/ogg", "audio/wav"],
        "browser_fallback_mime_types": ["audio/webm"],
    }
