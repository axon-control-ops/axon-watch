"""Vault runtime env injection and operator-safe posture (extracted from operations)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from app.vault.session import VaultSession


def _runtime_provider_ids() -> dict[str, str]:
    """Load sibling aliases even when control-plane owns the shared ``app`` package."""
    try:
        from app.vault.provider_aliases import RUNTIME_PROVIDER_IDS

        return RUNTIME_PROVIDER_IDS
    except ModuleNotFoundError:
        path = Path(__file__).resolve().parent / "provider_aliases.py"
        spec = importlib.util.spec_from_file_location("axon_watch_vault_provider_aliases", path)
        if spec is None or spec.loader is None:
            raise ImportError(f"unable to load vault provider aliases from {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return dict(module.RUNTIME_PROVIDER_IDS)


def vault_runtime_env() -> dict[str, str]:
    """Resolve CLI runtime env keys from unlocked vault (internal control-plane use only)."""
    from app.vault.operations import vault_resolve_named_secret, vault_resolve_provider_key

    if not VaultSession.is_unlocked():
        return {}

    env: dict[str, str] = {}
    named_bindings = (
        ("CURSOR_API_KEY", "cursor_cli"),
        ("CODEX_API_KEY", "codex_cli"),
        ("OPENAI_API_KEY", "openai_gpts"),
        ("ANTHROPIC_API_KEY", "anthropic"),
    )
    for env_name, provider_id in named_bindings:
        value = vault_resolve_named_secret(env_name) or vault_resolve_provider_key(provider_id)
        if value:
            env[env_name] = value
    if "CODEX_API_KEY" not in env and env.get("OPENAI_API_KEY"):
        env["CODEX_API_KEY"] = env["OPENAI_API_KEY"]
    azure_key_names = ("AZURE_SPEECH_KEY", "azure_speech_key")
    azure_region_names = ("AZURE_SPEECH_REGION", "azure_speech_region")
    for name in azure_key_names:
        value = vault_resolve_named_secret(name)
        if value:
            env.setdefault("AZURE_SPEECH_KEY", value)
            break
    for name in azure_region_names:
        value = vault_resolve_named_secret(name)
        if value:
            env.setdefault("AZURE_SPEECH_REGION", value)
            break
    google_api_key_names = (
        "AXON_WATCH_GOOGLE_CSE_API_KEY",
        "GOOGLE_SEARCH_API_KEY",
        "EXPO_PUBLIC_GOOGLE_CSE_API_KEY",
        "google_cse_api_key",
    )
    google_cx_names = (
        "AXON_WATCH_GOOGLE_CSE_CX",
        "GOOGLE_CSE_ID",
        "EXPO_PUBLIC_GOOGLE_CSE_CX",
        "google_cse_cx",
    )
    for name in google_api_key_names:
        value = vault_resolve_named_secret(name)
        if value:
            env.setdefault("AXON_WATCH_GOOGLE_CSE_API_KEY", value)
            break
    for name in google_cx_names:
        value = vault_resolve_named_secret(name)
        if value:
            env.setdefault("AXON_WATCH_GOOGLE_CSE_CX", value)
            break
    searxng_url = vault_resolve_named_secret("AXON_WATCH_SEARXNG_URL")
    if searxng_url:
        env.setdefault("AXON_WATCH_SEARXNG_URL", searxng_url)
    for _runtime_id, provider_id in _runtime_provider_ids().items():
        if provider_id in {binding[1] for binding in named_bindings}:
            continue
        value = vault_resolve_provider_key(provider_id)
        if value and provider_id == "cursor_cli":
            env.setdefault("CURSOR_API_KEY", value)
        if value and provider_id == "codex_cli":
            env.setdefault("CODEX_API_KEY", value)
            env.setdefault("OPENAI_API_KEY", value)
        if value and provider_id == "anthropic":
            env.setdefault("ANTHROPIC_API_KEY", value)
    return env


def vault_runtime_posture() -> dict[str, object]:
    """Operator-safe runtime vault posture (no secret values)."""
    from app.vault.operations import (
        vault_resolve_all_provider_keys,
        vault_resolve_named_secret,
    )

    unlocked = VaultSession.is_unlocked()
    resolved_map = vault_resolve_all_provider_keys() if unlocked else {}
    runtime_provider_ids = _runtime_provider_ids()
    runtime_keys: dict[str, bool] = {}
    for runtime_id, provider_id in runtime_provider_ids.items():
        runtime_keys[runtime_id] = bool(resolved_map.get(provider_id))
    named_keys = {
        "CURSOR_API_KEY": bool(vault_resolve_named_secret("CURSOR_API_KEY")) if unlocked else False,
        "CODEX_API_KEY": bool(vault_resolve_named_secret("CODEX_API_KEY")) if unlocked else False,
        "OPENAI_API_KEY": bool(vault_resolve_named_secret("OPENAI_API_KEY")) if unlocked else False,
        "ANTHROPIC_API_KEY": bool(vault_resolve_named_secret("ANTHROPIC_API_KEY")) if unlocked else False,
        "AZURE_SPEECH_KEY": bool(
            vault_resolve_named_secret("AZURE_SPEECH_KEY")
            or vault_resolve_named_secret("azure_speech_key")
        )
        if unlocked
        else False,
        "AZURE_SPEECH_REGION": bool(
            vault_resolve_named_secret("AZURE_SPEECH_REGION")
            or vault_resolve_named_secret("azure_speech_region")
        )
        if unlocked
        else False,
        "AXON_WATCH_GOOGLE_CSE_API_KEY": bool(
            vault_resolve_named_secret("AXON_WATCH_GOOGLE_CSE_API_KEY")
            or vault_resolve_named_secret("GOOGLE_SEARCH_API_KEY")
            or vault_resolve_named_secret("EXPO_PUBLIC_GOOGLE_CSE_API_KEY")
            or vault_resolve_named_secret("google_cse_api_key")
        )
        if unlocked
        else False,
        "AXON_WATCH_GOOGLE_CSE_CX": bool(
            vault_resolve_named_secret("AXON_WATCH_GOOGLE_CSE_CX")
            or vault_resolve_named_secret("GOOGLE_CSE_ID")
            or vault_resolve_named_secret("EXPO_PUBLIC_GOOGLE_CSE_CX")
            or vault_resolve_named_secret("google_cse_cx")
        )
        if unlocked
        else False,
        "AXON_WATCH_SEARXNG_URL": bool(vault_resolve_named_secret("AXON_WATCH_SEARXNG_URL"))
        if unlocked
        else False,
    }
    for env_name, present in named_keys.items():
        if present:
            if env_name == "CURSOR_API_KEY":
                runtime_keys["cursor_local"] = True
                runtime_keys["cursor_cloud"] = True
            if env_name in {"CODEX_API_KEY", "OPENAI_API_KEY"}:
                runtime_keys["codex_local"] = True
                runtime_keys["codex_cloud"] = True
            if env_name == "ANTHROPIC_API_KEY":
                runtime_keys["claude_local"] = True
                runtime_keys["claude_cloud"] = True

    if not unlocked:
        posture = "vault_locked"
        hint = "Unlock /vault to inject provider keys into Cursor, Claude, and Codex runtimes."
    elif any(runtime_keys.values()):
        posture = "ready"
        hint = "Vault provider keys are available for CLI runtimes."
    else:
        posture = "missing_keys"
        hint = (
            "Vault is unlocked but no Cursor/Claude/Codex/OpenAI API keys were found. "
            "Runtimes may still work via CLI subscription login on the host "
            "(`cursor agent login`, `claude auth login`, `codex login`). See HOW-TO-HANDBOOK → Runtime auth."
        )

    return {
        "unlocked": unlocked,
        "posture": posture,
        "hint": hint,
        "runtime_keys": runtime_keys,
        "provider_keys": {
            provider_id: bool(resolved_map.get(provider_id))
            for provider_id in sorted(set(runtime_provider_ids.values()))
        },
    }
