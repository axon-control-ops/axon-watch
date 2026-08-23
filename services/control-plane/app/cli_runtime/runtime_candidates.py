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
    *,
    fallback_runtime_families: tuple[str, ...] = (),
) -> list[dict[str, object]]:
    candidates = ordered_runtime_candidates(snapshot)
    preferred = str(runtime_target or "").strip()
    if not preferred:
        return candidates
    by_id = {str(record.get("id") or ""): record for record in candidates}
    selected = by_id.get(preferred)
    # A value passed by an interactive composer remains a strict operator
    # selection. Autonomous workers may additionally supply the workspace's
    # explicitly approved Auto families; keep the selected runtime first and
    # never consume an unapproved provider.
    if not selected:
        return []
    allowed = {str(family).strip() for family in fallback_runtime_families if family}
    if not allowed:
        return [selected]
    return [
        selected,
        *[
            record
            for record in candidates
            if record is not selected and str(record.get("family") or "") in allowed
        ],
    ]


__all__ = ["effective_cli_model", "ordered_candidates_for_dispatch"]
