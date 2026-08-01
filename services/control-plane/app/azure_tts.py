"""Minimal Azure Speech synthesis for KAIRO playback (axon-local SSML parity)."""

from __future__ import annotations

import http.client
import os
import re
import time
import urllib.error
import urllib.request
from xml.sax.saxutils import escape

from app.voice_tuning import (
    DEFAULT_VOICE_PITCH,
    DEFAULT_VOICE_RATE,
    azure_voice_pitch_attr,
    azure_voice_rate_attr,
)

DEFAULT_AZURE_VOICE = "en-GB-RyanNeural"
DEFAULT_AZURE_REGION = "southafricanorth"
# RyanNeural is natively 48 kHz — requesting 24 kHz downsampled and dulled the voice.
DEFAULT_AZURE_OUTPUT_FORMAT = "audio-48khz-192kbitrate-mono-mp3"
# Runtime evidence: Chromium reported fully buffered audio at currentTime=0,
# yet the sink dropped roughly the first 400–500 ms ("Continuing" → "uing").
# Encoded silence survives decoder/device wake-up; a JS delay before play does not.
# Bumped past 650ms — stand-up lines still clipped openings on some sinks.
LEADING_AUDIO_GUARD_MS = 1100
# Soft action-word openings still lost the first syllable at 1450 ms
# ("Walking" -> "king"). Keep the extra latency on vulnerable openings only.
SOFT_ONSET_LEADING_AUDIO_GUARD_MS = 2200
# Continuation chunks already have a live audio graph — do not re-pad 1s+.
CONTINUATION_LEADING_AUDIO_GUARD_MS = 60
TTS_READ_ATTEMPTS = 2
TTS_REQUEST_TIMEOUT_SECONDS = 6
TTS_RETRY_BACKOFF_SECONDS = 0.15
_PLACEHOLDER_KEYS = frozenset({"changeme", "change-me", "placeholder", "your-key-here", "test"})
_AZURE_KEY_NAMES = ("AZURE_SPEECH_KEY", "azure_speech_key")
_AZURE_REGION_NAMES = ("AZURE_SPEECH_REGION", "azure_speech_region")
_SOFT_ONSET_OPENING_RE = re.compile(
    r"^(?:building|checking|continuing|looking|pulling|reading|reviewing|"
    r"walking|working|watching|writing)\b",
    flags=re.IGNORECASE,
)


def _clean_for_speech(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", str(text or "").strip())
    # Last-resort TTS safety: never letter-spell the persona name.
    cleaned = re.sub(
        r"\bV\s*[.\-]\s*A\s*[.\-]\s*X\s*[.\-]\s*O\s*[.\-]\s*N\b",
        "Vekson",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\bV\s+A\s+X\s+O\s+N\b", "Vekson", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bVAXON\b", "Vekson", cleaned, flags=re.IGNORECASE)
    # Sesotho name — TA-bo, not THA-bo.
    cleaned = re.sub(r"\bThabo\b", "Ta-bo", cleaned, flags=re.IGNORECASE)
    # Zulu names Azure often misreads — speak Sipho as SEE-po.
    cleaned = re.sub(r"\bSipho\b", "See-po", cleaned, flags=re.IGNORECASE)
    return cleaned[:3000]


def leading_audio_guard_ms(text: str, *, continuation: bool = False) -> int:
    """Return encoded lead-in required for the opening phoneme."""
    if continuation:
        return CONTINUATION_LEADING_AUDIO_GUARD_MS
    cleaned = _clean_for_speech(text)
    if _SOFT_ONSET_OPENING_RE.match(cleaned):
        return SOFT_ONSET_LEADING_AUDIO_GUARD_MS
    return LEADING_AUDIO_GUARD_MS


def _inject_ssml_breaks(text: str) -> str:
    """Insert short pauses so delivery is conversational (axon-local parity)."""
    value = str(text or "")
    if not value:
        return value
    # Keep breaks crisp — 120ms+ stacked with em-dashes / commas felt laggy.
    value = re.sub(r"([.!?])\s+", r"\1<break time='70ms'/> ", value)
    value = re.sub(r":\s+", r":<break time='45ms'/> ", value)
    value = re.sub(r";\s+", r";<break time='45ms'/> ", value)
    value = re.sub(r"\s*[—–]\s*", r"<break time='45ms'/> ", value)
    value = re.sub(
        r",\s+(?=(?:and|but|or|so|yet|because|since|while|although)\b)",
        r",<break time='40ms'/> ",
        value,
    )
    return value


def _escape_ssml_text_preserving_breaks(text: str) -> str:
    break_tag = re.compile(r"(<break time='(?:40|45|70|80|90|120)ms'/>)")
    parts = break_tag.split(str(text or ""))
    escaped_parts: list[str] = []
    for part in parts:
        if not part:
            continue
        if break_tag.fullmatch(part):
            escaped_parts.append(part)
        else:
            escaped_parts.append(escape(part, {"'": "&apos;", '"': "&quot;"}))
    return "".join(escaped_parts)


def extract_azure_speech_key(value: object) -> str:
    raw = str(value or "").strip()
    if not raw or raw.lower() in _PLACEHOLDER_KEYS:
        return ""
    return raw


def resolve_azure_speech_region(value: object) -> str:
    raw = str(value or "").strip()
    return raw or DEFAULT_AZURE_REGION


def _first_env_value(names: tuple[str, ...], env: dict[str, str]) -> str:
    for name in names:
        value = extract_azure_speech_key(env.get(name))
        if value:
            return value
    return ""


def _first_region_value(names: tuple[str, ...], env: dict[str, str]) -> str:
    for name in names:
        raw = str(env.get(name) or "").strip()
        if raw:
            return resolve_azure_speech_region(raw)
    return ""


def resolve_azure_speech_credentials() -> tuple[str, str]:
    """Resolve Azure Speech key/region from process env, then unlocked vault."""
    env = {key: str(value) for key, value in os.environ.items() if str(value or "").strip()}
    key = _first_env_value(_AZURE_KEY_NAMES, env)
    region = _first_region_value(_AZURE_REGION_NAMES, env) or DEFAULT_AZURE_REGION

    if key:
        return key, region

    try:
        from app.cli_runtime.vault_keys import runtime_vault_env

        vault_env = runtime_vault_env()
        key = _first_env_value(_AZURE_KEY_NAMES, vault_env)
        vault_region = _first_region_value(_AZURE_REGION_NAMES, vault_env)
        if vault_region:
            region = vault_region
    except Exception:
        key = ""

    return key, region


def azure_speech_configured() -> bool:
    key, _region = resolve_azure_speech_credentials()
    return bool(key)


def build_azure_ssml(
    text: str,
    *,
    voice: str = DEFAULT_AZURE_VOICE,
    rate: float | int | str | None = None,
    pitch: float | int | str | None = None,
    continuation: bool = False,
) -> str:
    """Build SSML matching axon-local Azure talkback.

    - Relative prosody rate/pitch (e.g. ``-15%``, ``+4%``) — not absolute ``85%``
    - Sentence/colon breaks for natural pacing
    - No ``mstts:express-as style=chat`` (that style races past operator pacing)
    """
    safe_voice = escape(voice, {"'": "&apos;", '"': "&quot;"})
    cleaned = _clean_for_speech(text)
    safe_text = _escape_ssml_text_preserving_breaks(_inject_ssml_breaks(cleaned))
    rate_attr = azure_voice_rate_attr(rate if rate is not None else DEFAULT_VOICE_RATE)
    pitch_attr = azure_voice_pitch_attr(pitch if pitch is not None else DEFAULT_VOICE_PITCH)
    leading_guard_ms = leading_audio_guard_ms(cleaned, continuation=continuation)
    # First chunk: mstts Leading + short outside-prosody break for sink wake-up.
    # Continuations: tiny lead only — stacked 1.1s+200ms made mid-speech laggy.
    onset_break = "" if continuation else "<break time='120ms'/>"
    return (
        "<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' "
        "xmlns:mstts='https://www.w3.org/2001/mstts' xml:lang='en-GB'>"
        f"<voice name='{safe_voice}'>"
        f"<mstts:silence type='Leading' value='{leading_guard_ms}ms'/>"
        f"{onset_break}"
        f"<prosody rate='{rate_attr}' pitch='{pitch_attr}'>"
        f"{safe_text}</prosody></voice>"
        "</speak>"
    )


def synthesize_azure_speech(
    text: str,
    *,
    voice: str = DEFAULT_AZURE_VOICE,
    region: str | None = None,
    key: str | None = None,
    rate: float | None = None,
    pitch: float | None = None,
    continuation: bool = False,
) -> tuple[bytes, str] | None:
    resolved_key, resolved_region = resolve_azure_speech_credentials()
    speech_key = extract_azure_speech_key(key) or resolved_key
    if not speech_key:
        return None

    trimmed = _clean_for_speech(text)
    if not trimmed:
        return None

    speech_region = resolve_azure_speech_region(region or resolved_region)
    url = f"https://{speech_region}.tts.speech.microsoft.com/cognitiveservices/v1"
    body = build_azure_ssml(
        trimmed,
        voice=voice,
        rate=rate,
        pitch=pitch,
        continuation=continuation,
    ).encode("utf-8")
    headers = {
        "Ocp-Apim-Subscription-Key": speech_key,
        "Content-Type": "application/ssml+xml",
        "X-Microsoft-OutputFormat": DEFAULT_AZURE_OUTPUT_FORMAT,
        "User-Agent": "axon-watch-control-plane",
    }

    # IncompleteRead used to escape as a 500 and tear stand-up audio mid-line.
    # Retry quietly; fall back to browser TTS via available=false.
    last_error: Exception | None = None
    for attempt in range(TTS_READ_ATTEMPTS):
        request = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=TTS_REQUEST_TIMEOUT_SECONDS) as response:
                payload = response.read()
                content_type = response.headers.get("Content-Type", "audio/mpeg")
                if not payload:
                    return None
                return payload, content_type
        except http.client.IncompleteRead as exc:
            last_error = exc
            if attempt + 1 < TTS_READ_ATTEMPTS:
                time.sleep(TTS_RETRY_BACKOFF_SECONDS * (attempt + 1))
                continue
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
            last_error = exc
            break
    _ = last_error
    return None
