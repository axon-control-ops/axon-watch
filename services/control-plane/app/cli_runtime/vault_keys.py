"""Fetch vault-fed runtime keys from axon-watch (internal only)."""

from __future__ import annotations

import copy
import os
import time
from typing import Any

from app.vault import watch_adapter

_RUNTIME_CONTEXT_CACHE: dict[str, Any] = {"fetched_at": 0.0, "payload": None}
_CACHE_TTL_SECONDS = 15.0


def _fetch_runtime_context(*, force_refresh: bool = False) -> dict[str, Any]:
    cached = _RUNTIME_CONTEXT_CACHE.get("payload")
    fetched_at = float(_RUNTIME_CONTEXT_CACHE.get("fetched_at") or 0.0)
    if not force_refresh and cached is not None and (time.monotonic() - fetched_at) < _CACHE_TTL_SECONDS:
        return copy.deepcopy(cached)

    runtime_posture: dict[str, Any] | None = None
    try:
        posture_payload = watch_adapter.request_json("GET", "/internal/watch/vault/runtime-posture")
        candidate = posture_payload.get("vault_runtime")
        if isinstance(candidate, dict):
            runtime_posture = candidate
    except RuntimeError as exc:
        runtime_posture = {
            "unlocked": False,
            "posture": "vault_locked",
            "hint": f"Vault runtime posture unavailable. {exc}",
            "runtime_keys": {},
            "provider_keys": {},
        }
    if runtime_posture is None:
        runtime_posture = {
            "unlocked": False,
            "posture": "vault_locked",
            "hint": "Vault runtime posture unavailable.",
            "runtime_keys": {},
            "provider_keys": {},
        }

    env_payload: dict[str, str] = {}
    if runtime_posture.get("unlocked"):
        try:
            env_response = watch_adapter.request_json("GET", "/internal/watch/vault/runtime-env")
            raw_env = env_response.get("env")
            if isinstance(raw_env, dict):
                env_payload = {
                    str(key): str(value)
                    for key, value in raw_env.items()
                    if str(key).strip() and str(value).strip()
                }
        except RuntimeError:
            env_payload = {}

    payload = {"vault_runtime": runtime_posture, "env": env_payload}
    _RUNTIME_CONTEXT_CACHE["fetched_at"] = time.monotonic()
    _RUNTIME_CONTEXT_CACHE["payload"] = copy.deepcopy(payload)
    return copy.deepcopy(payload)


def fetch_runtime_context(*, force_refresh: bool = False) -> dict[str, Any]:
    return _fetch_runtime_context(force_refresh=force_refresh)


def runtime_vault_posture(*, force_refresh: bool = False) -> dict[str, Any]:
    return dict(fetch_runtime_context(force_refresh=force_refresh).get("vault_runtime") or {})


def runtime_vault_env(*, force_refresh: bool = False) -> dict[str, str]:
    return dict(fetch_runtime_context(force_refresh=force_refresh).get("env") or {})


def runtime_has_vault_key(runtime_id: str, *, force_refresh: bool = False) -> bool:
    posture = runtime_vault_posture(force_refresh=force_refresh)
    runtime_keys = posture.get("runtime_keys")
    if isinstance(runtime_keys, dict):
        return bool(runtime_keys.get(runtime_id))
    return False


def runtime_subprocess_env(*, force_refresh: bool = False) -> dict[str, str]:
    merged = dict(os.environ)
    vault_env = runtime_vault_env(force_refresh=force_refresh)
    for key, value in vault_env.items():
        if not str(merged.get(key, "")).strip():
            merged[key] = value
    return merged


def invalidate_runtime_vault_cache() -> None:
    _RUNTIME_CONTEXT_CACHE["fetched_at"] = 0.0
    _RUNTIME_CONTEXT_CACHE["payload"] = None
