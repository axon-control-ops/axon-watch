"""Cursor CLI model policy — Auto/Composer vs API-billed models.

Continuous workers must stay on Auto or Composer unless the operator
explicitly pinned an API model in the workspace Agent Dock composer.
"""

from __future__ import annotations

import os
import re

_MODEL_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,118}$")


def is_cursor_auto_model(model_id: str | None) -> bool:
    normalized = str(model_id or "").strip().lower()
    return not normalized or normalized == "auto"


def is_cursor_composer_model(model_id: str | None) -> bool:
    return str(model_id or "").strip().lower().startswith("composer-")


def is_cursor_api_model(model_id: str | None) -> bool:
    """Named models outside Auto/Composer — typically API-pool billed."""
    return not is_cursor_auto_model(model_id) and not is_cursor_composer_model(model_id)


def normalize_model_id(model_id: str | None) -> str:
    value = str(model_id or "").strip()
    if not value:
        return ""
    if value.lower() == "auto":
        return "auto"
    if _MODEL_ID_RE.fullmatch(value):
        return value[:120]
    return ""


def resolve_cli_model_for_dispatch(
    family: str,
    runtime_model: str | None,
    *,
    trust_policy: str = "operator",
) -> str:
    """Resolve the CLI ``--model`` value for a dispatch.

    Returns empty string to omit ``--model`` (Cursor Auto).

    Worker policy:
    - Empty / auto → Auto (omit). Never inherit ``AXON_WATCH_CURSOR_MODEL``.
    - Composer ids → allowed.
    - API/named ids → allowed only when explicitly passed as ``runtime_model``
      (workspace composer pin). Env alone never injects API models for workers.

    Operator policy:
    - Preserve prior behavior: empty/auto may fall back to env model.
    """
    policy = str(trust_policy or "operator").strip().lower() or "operator"
    family_key = str(family or "").strip().lower()
    explicit = normalize_model_id(runtime_model)

    if policy == "worker":
        if is_cursor_auto_model(explicit):
            return ""
        if family_key == "cursor":
            # Composer or explicit API pin from workspace composer prefs.
            return "" if explicit.lower() == "auto" else explicit
        # Codex worker: allow explicit non-auto; ignore env.
        return "" if is_cursor_auto_model(explicit) else explicit

    # Operator / interactive Agent Dock — existing env fallback.
    normalized = explicit
    if is_cursor_auto_model(normalized):
        env_key = {
            "cursor": "AXON_WATCH_CURSOR_MODEL",
            "claude": "AXON_WATCH_CLAUDE_MODEL",
        }.get(family_key, "AXON_WATCH_CODEX_MODEL")
        normalized = normalize_model_id(os.environ.get(env_key, ""))
    if is_cursor_auto_model(normalized):
        return ""
    return normalized if normalized.lower() != "auto" else ""
