"""Codex CLI model catalog discovery for Axon-X runtime surfaces."""

from __future__ import annotations

import json
import os
import time
from typing import Any

from app.cli_runtime.catalog import (
    StatusRecord,
    _codex_auth_status,
    _run_command,
    find_codex_cli,
)
from app.cli_runtime.runtime_auth import codex_dispatch_env
from app.cli_runtime.vault_keys import fetch_runtime_context

ModelRecord = dict[str, Any]
StatusPayload = dict[str, Any]

_LIST_MODELS_TIMEOUT_SECONDS = 20
_MODEL_CACHE: dict[str, tuple[float, list[ModelRecord]]] = {}
_MODEL_CACHE_TTL_SECONDS = 300.0


def _normalize_model_record(record: object) -> ModelRecord | None:
    if not isinstance(record, dict) or str(record.get("visibility") or "") != "list":
        return None
    model_id = str(record.get("slug") or "").strip()
    if not model_id:
        return None
    model: ModelRecord = {
        "id": model_id,
        "label": str(record.get("display_name") or model_id).strip() or model_id,
        "description": str(record.get("description") or "Codex model available to this account.").strip(),
    }
    reasoning = str(record.get("default_reasoning_level") or "").strip()
    if reasoning:
        model["badge"] = reasoning.capitalize()
        model["default_reasoning_level"] = reasoning
    supported_reasoning = record.get("supported_reasoning_levels")
    if isinstance(supported_reasoning, list):
        levels = [
            str(item.get("effort") or "").strip().lower()
            for item in supported_reasoning
            if isinstance(item, dict) and str(item.get("effort") or "").strip()
        ]
        if levels:
            model["reasoning_levels"] = levels
    return model


def _fetch_codex_models(binary: str, *, env: dict[str, str]) -> list[ModelRecord]:
    try:
        proc = _run_command(
            [binary, "debug", "models"],
            timeout=_LIST_MODELS_TIMEOUT_SECONDS,
            env=env,
        )
    except Exception:
        return []
    if proc.returncode != 0:
        return []
    try:
        payload = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return []
    raw_models = payload.get("models") if isinstance(payload, dict) else None
    if not isinstance(raw_models, list):
        return []
    models: list[ModelRecord] = []
    seen: set[str] = set()
    for raw_model in raw_models:
        normalized = _normalize_model_record(raw_model)
        if normalized is None or normalized["id"] in seen:
            continue
        seen.add(normalized["id"])
        models.append(normalized)
    return models


def list_codex_models(binary: str = "", *, env: dict[str, str] | None = None) -> list[ModelRecord]:
    if not binary:
        return []
    cache_key = os.path.realpath(binary) if os.path.exists(binary) else binary
    cached = _MODEL_CACHE.get(cache_key)
    now = time.monotonic()
    if cached and (now - cached[0]) < _MODEL_CACHE_TTL_SECONDS:
        return [dict(item) for item in cached[1]]
    models = _fetch_codex_models(binary, env=env or dict(os.environ))
    if models:
        _MODEL_CACHE[cache_key] = (now, models)
    return [dict(item) for item in models]


def default_codex_model(binary: str, *, env: dict[str, str]) -> str:
    """Return the account's first selectable Codex model, never a config-only id."""
    return next(
        (
            str(model.get("id") or "").strip()
            for model in list_codex_models(binary, env=env)
            if str(model.get("id") or "").strip()
        ),
        "",
    )


def codex_runtime_snapshot(*, force_refresh: bool = False) -> StatusPayload:
    context = fetch_runtime_context(force_refresh=force_refresh)
    vault_posture = dict(context.get("vault_runtime") or {})
    merged_env = dict(os.environ)
    for key, value in dict(context.get("env") or {}).items():
        if not str(merged_env.get(key, "")).strip():
            merged_env[key] = value
    vault_env_only = {
        key: value
        for key, value in merged_env.items()
        if key in {"CODEX_API_KEY", "OPENAI_API_KEY"}
        and value
        and not str(os.environ.get(key, "")).strip()
    }
    binary = find_codex_cli(os.environ.get("AXON_WATCH_CODEX_CLI_PATH", "").strip())
    auth: StatusRecord = _codex_auth_status(
        binary,
        vault_posture=vault_posture,
        env_keys=vault_env_only,
        probe_env=merged_env,
    )
    # A signed-in ChatGPT account is the source of truth for this catalog.  Do not
    # let a stale key in the service environment silently replace that session.
    live_models = list_codex_models(
        binary,
        env=codex_dispatch_env(merged_env, auth=auth),
    ) if binary else []
    return {
        "installed": bool(binary),
        "binary": binary,
        "auth": auth,
        "available_models": live_models,
        "codex_models": [],
        "catalog_source": "live" if live_models else "unavailable",
    }
