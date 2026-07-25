"""Cursor CLI model catalog discovery for Axon-X runtime surfaces."""

from __future__ import annotations

import os
import re
import time
from typing import Any

from app.cli_runtime.catalog import (
    StatusRecord,
    _cursor_auth_status,
    _run_command,
    find_cursor_cli,
)
from app.cli_runtime.vault_keys import fetch_runtime_context

ModelRecord = dict[str, str]
StatusPayload = dict[str, Any]

_CURSOR_MODEL_LINE_RE = re.compile(r"^(\S+)\s+-\s+(.+)$")
_MODEL_BADGE_RE = re.compile(r"\b(Fast|High|Medium|Low|Max)\b", re.IGNORECASE)
_LIST_MODELS_TIMEOUT_SECONDS = 20
_MODEL_CACHE: dict[str, tuple[float, list[ModelRecord]]] = {}
_MODEL_CACHE_TTL_SECONDS = 300.0

CURSOR_CLI_MODEL_OPTIONS: list[ModelRecord] = [
    {
        "id": "auto",
        "label": "Auto",
        "description": "Balanced quality and speed — Cursor picks the best model per request.",
    },
    {
        "id": "composer-2.5-fast",
        "label": "Composer 2.5 Fast",
        "description": "Cursor Composer model (subscription routing, default).",
    },
    {
        "id": "composer-2.5",
        "label": "Composer 2.5",
        "description": "Cursor Composer model (subscription routing).",
    },
    {
        "id": "claude-fable-5-thinking-high",
        "label": "claude-fable-5-thinking-high",
        "description": "Claude Fable 5 (high thinking) via Cursor subscription routing.",
    },
    {
        "id": "gpt-5.4",
        "label": "gpt-5.4",
        "description": "GPT model via Cursor subscription routing.",
    },
    {
        "id": "claude-sonnet-4.6",
        "label": "claude-sonnet-4.6",
        "description": "Claude Sonnet via Cursor subscription routing.",
    },
]


def _normalize_model_badge(text: str) -> str:
    match = _MODEL_BADGE_RE.search(str(text or ""))
    if not match:
        return ""
    return match.group(1).capitalize()


def _normalize_model_record(model_id: str, label: str) -> ModelRecord:
    clean_id = model_id.strip()
    clean_label = label.strip() or clean_id
    badge = _normalize_model_badge(clean_label)
    description = clean_label
    if badge:
        description = _MODEL_BADGE_RE.sub("", clean_label).strip(" ·-")
    record: ModelRecord = {
        "id": clean_id,
        "label": clean_label,
        "description": description or clean_label,
    }
    if badge:
        record["badge"] = badge
    return record


def _fetch_cursor_models(binary: str) -> list[ModelRecord]:
    try:
        proc = _run_command(
            [binary, "agent", "--list-models"],
            timeout=_LIST_MODELS_TIMEOUT_SECONDS,
        )
    except Exception:
        return []
    text = (proc.stdout or proc.stderr or "").strip()
    if proc.returncode != 0 or "Available models" not in text:
        return []
    models: list[ModelRecord] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line == "Available models":
            continue
        match = _CURSOR_MODEL_LINE_RE.match(line)
        if not match:
            continue
        model_id = match.group(1).strip()
        label = match.group(2).strip()
        if not model_id:
            continue
        models.append(_normalize_model_record(model_id, label))
    return models


def list_cursor_models(binary: str = "") -> list[ModelRecord]:
    if not binary:
        return []
    cache_key = os.path.realpath(binary) if os.path.exists(binary) else binary
    cached = _MODEL_CACHE.get(cache_key)
    now = time.monotonic()
    if cached and (now - cached[0]) < _MODEL_CACHE_TTL_SECONDS:
        return [dict(item) for item in cached[1]]
    models = _fetch_cursor_models(binary)
    if models:
        _MODEL_CACHE[cache_key] = (now, models)
    return [dict(item) for item in models]


def cursor_runtime_snapshot(*, force_refresh: bool = False) -> StatusPayload:
    context = fetch_runtime_context(force_refresh=force_refresh)
    vault_posture = dict(context.get("vault_runtime") or {})
    merged_env = dict(os.environ)
    for key, value in dict(context.get("env") or {}).items():
        if not str(merged_env.get(key, "")).strip():
            merged_env[key] = value
    vault_env_only = {
        key: value
        for key, value in merged_env.items()
        if key in {"CURSOR_API_KEY", "CODEX_API_KEY", "OPENAI_API_KEY"}
        and value
        and not str(os.environ.get(key, "")).strip()
    }

    binary = find_cursor_cli(os.environ.get("AXON_WATCH_CURSOR_CLI_PATH", "").strip())
    live_models = list_cursor_models(binary) if binary else []
    fallback_models = [dict(item) for item in CURSOR_CLI_MODEL_OPTIONS]
    auth: StatusRecord = _cursor_auth_status(
        binary,
        vault_posture=vault_posture,
        env_keys=vault_env_only,
        probe_env=merged_env,
    )

    return {
        "installed": bool(binary),
        "binary": binary,
        "auth": auth,
        "available_models": live_models if live_models else fallback_models,
        "cursor_models": fallback_models,
        "catalog_source": "live" if live_models else "fallback",
    }
