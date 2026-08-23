"""Claude Code CLI model catalog for Axon-X runtime surfaces.

Unlike Cursor, the `claude` CLI has no `--list-models`-style discovery
command — `--model` just accepts a fixed set of aliases ('sonnet', 'opus',
'haiku') or a full model name. So this catalog is a static curated list,
not a live probe + cache like `cursor_models.py`.
"""

from __future__ import annotations

import os
from typing import Any

from app.cli_runtime.catalog import (
    StatusRecord,
    _claude_auth_status,
    find_claude_cli,
)
from app.cli_runtime.vault_keys import fetch_runtime_context

ModelRecord = dict[str, str]
StatusPayload = dict[str, Any]

CLAUDE_CLI_MODEL_OPTIONS: list[ModelRecord] = [
    {
        "id": "auto",
        "label": "Auto",
        "description": "Let Claude Code choose model and effort automatically.",
        "effort": "",
    },
    # Sonnet 4.6 — default workhorse; three effort tiers
    # Effort values must match claude CLI --effort flag: low|medium|high|xhigh|max
    {
        "id": "sonnet",
        "label": "Sonnet",
        "description": "Balanced quality and speed — Claude Code's default.",
        "badge": "default",
        "effort": "medium",
    },
    {
        "id": "sonnet@low",
        "label": "Sonnet · Low",
        "description": "Reduced extended thinking — fastest responses.",
        "effort": "low",
    },
    {
        "id": "sonnet@high",
        "label": "Sonnet · High",
        "description": "Increased extended thinking — more thorough analysis.",
        "effort": "high",
    },
    {
        "id": "sonnet@max",
        "label": "Sonnet · Max",
        "description": "Maximum extended thinking — most thorough, slowest.",
        "effort": "max",
    },
    # Opus 4.8 — highest capability
    {
        "id": "opus",
        "label": "Opus",
        "description": "Highest capability — deeper reasoning, slower per request.",
        "effort": "medium",
    },
    {
        "id": "opus@high",
        "label": "Opus · High",
        "description": "Opus with high extended thinking — for complex problems.",
        "effort": "high",
    },
    {
        "id": "opus@max",
        "label": "Opus · Max",
        "description": "Opus with maximum extended thinking — hardest problems only.",
        "effort": "max",
    },
    # Haiku 4.5 — fast and economical
    {
        "id": "haiku",
        "label": "Haiku",
        "description": "Fastest and most economical — for lighter, well-scoped tasks.",
        "effort": "low",
    },
]


def claude_runtime_snapshot(*, force_refresh: bool = False) -> StatusPayload:
    context = fetch_runtime_context(force_refresh=force_refresh)
    vault_posture = dict(context.get("vault_runtime") or {})
    merged_env = dict(os.environ)
    for key, value in dict(context.get("env") or {}).items():
        if not str(merged_env.get(key, "")).strip():
            merged_env[key] = value
    vault_env_only = {
        key: value
        for key, value in merged_env.items()
            if key in {"CURSOR_API_KEY", "CODEX_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"}
        and value
        and not str(os.environ.get(key, "")).strip()
    }

    binary = find_claude_cli(os.environ.get("AXON_WATCH_CLAUDE_CLI_PATH", "").strip())
    fallback_models = [dict(item) for item in CLAUDE_CLI_MODEL_OPTIONS]
    auth: StatusRecord = _claude_auth_status(
        binary,
        vault_posture=vault_posture,
        env_keys=vault_env_only,
        probe_env=merged_env,
    )

    return {
        "installed": bool(binary),
        "binary": binary,
        "auth": auth,
        "available_models": fallback_models,
        "claude_models": fallback_models,
        # The claude CLI has no live model-listing command, so this catalog
        # is always the static curated list — never "live" like Cursor's.
        "catalog_source": "static",
    }
