"""Ordering helpers for preferred and fallback local runtime targets."""

from __future__ import annotations

import os

from app.cli_runtime.recovery import ordered_runtime_candidates


def effective_cli_model(family: str, runtime_model: str) -> str:
    normalized = str(runtime_model or "").strip()
    if not normalized or normalized.lower() == "auto":
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
    if not selected:
        return candidates
    return [selected, *(
        record
        for record in candidates
        if str(record.get("id") or "") not in {"", preferred}
    )]


__all__ = ["effective_cli_model", "ordered_candidates_for_dispatch"]
