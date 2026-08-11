"""Ordering helpers for runtime selection and automatic fallback."""

from __future__ import annotations

import os

from app.cli_runtime.recovery import ordered_runtime_candidates


def effective_cli_model(family: str, runtime_model: str) -> str:
    normalized = str(runtime_model or "").strip()
    if not normalized or normalized.lower() == "auto":
        # Codex has no Cursor-style Auto routing and its config may hold a
        # stale model id, so leave it empty here — callers fall back to the
        # account's live model catalog (see default_codex_model) instead.
        if family == "codex":
            return ""
        env_key = {
            "cursor": "AXON_WATCH_CURSOR_MODEL",
            "claude": "AXON_WATCH_CLAUDE_MODEL",
        }.get(family, "AXON_WATCH_CODEX_MODEL")
        normalized = str(os.environ.get(env_key, "")).strip()
    return "" if normalized.lower() == "auto" else normalized


def ordered_candidates_for_dispatch(
    snapshot: dict[str, object],
    runtime_target: str | None,
) -> list[dict[str, object]]:
    candidates = ordered_runtime_candidates(snapshot)
    preferred = str(runtime_target or "").strip()
    if not preferred:
        return candidates
    by_id = {str(record.get("id") or ""): record for record in candidates}
    selected = by_id.get(preferred)
    # A value passed by the composer is an explicit operator selection, not a
    # ranking hint. Falling through to another provider made the UI say Codex
    # while a failed turn actually consumed Claude/Cursor capacity. Automatic
    # fallback remains available only when the composer leaves the target auto.
    return [selected] if selected else []


__all__ = ["effective_cli_model", "ordered_candidates_for_dispatch"]
