"""Minimal Azure Speech synthesis for KAIRO playback."""

from __future__ import annotations

import os
import re
import urllib.error
import urllib.request
from xml.sax.saxutils import escape

DEFAULT_AZURE_VOICE = "en-GB-RyanNeural"
DEFAULT_AZURE_REGION = "southafricanorth"
# RyanNeural is natively 48 kHz — requesting 24 kHz downsampled and dulled the voice.
DEFAULT_AZURE_OUTPUT_FORMAT = "audio-48khz-192kbitrate-mono-mp3"
# Conversational delivery for assistant lines (Ryan supports cheerful + chat).
DEFAULT_AZURE_STYLE = "chat"
_CHAT_STYLE_VOICES = frozenset({"en-GB-RyanNeural"})
_PLACEHOLDER_KEYS = frozenset({"changeme", "change-me", "placeholder", "your-key-here", "test"})
_AZURE_KEY_NAMES = ("AZURE_SPEECH_KEY", "azure_speech_key")
_AZURE_REGION_NAMES = ("AZURE_SPEECH_REGION", "azure_speech_region")


def _clean_for_speech(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", str(text or "").strip())
    return cleaned[:3000]


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
    style: str | None = DEFAULT_AZURE_STYLE,
) -> str:
    """Build SSML for neural TTS.

    No rate/pitch prosody overrides — those dulled the voice. For Ryan, wrap in
    the supported ``chat`` style so lines sound conversational rather than flat.
    """
    safe_voice = escape(voice, {"'": "&apos;", '"': "&quot;"})
    safe_text = escape(_clean_for_speech(text), {"'": "&apos;", '"': "&quot;"})
    resolved_style = style if voice in _CHAT_STYLE_VOICES else None
    if resolved_style:
        safe_style = escape(resolved_style, {"'": "&apos;", '"': "&quot;"})
        inner = f"<mstts:express-as style='{safe_style}'>{safe_text}</mstts:express-as>"
    else:
        inner = safe_text
    return (
        "<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' "
        "xmlns:mstts='https://www.w3.org/2001/mstts' xml:lang='en-GB'>"
        f"<voice name='{safe_voice}'>{inner}</voice>"
        "</speak>"
    )


def synthesize_azure_speech(
    text: str,
    *,
    voice: str = DEFAULT_AZURE_VOICE,
    region: str | None = None,
    key: str | None = None,
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
    request = urllib.request.Request(
        url,
        data=build_azure_ssml(trimmed, voice=voice).encode("utf-8"),
        headers={
            "Ocp-Apim-Subscription-Key": speech_key,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": DEFAULT_AZURE_OUTPUT_FORMAT,
            "User-Agent": "axon-watch-control-plane",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            payload = response.read()
            content_type = response.headers.get("Content-Type", "audio/mpeg")
            if not payload:
                return None
            return payload, content_type
    except (urllib.error.URLError, TimeoutError, ValueError):
        return None
