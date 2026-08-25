"""Reap abandoned disposable worker checkouts before they exhaust /tmp.

``preserve_isolation`` (worker_dispatch.py) deliberately keeps a checkout on
disk after a blocked/failed publish so an operator can recover the work — but
nothing ever swept those preserved checkouts afterward. On this host that let
77 checkouts (7.9G) accumulate under a 9.8G tmpfs /tmp, which filled it to
100% and then made *every new* isolation fail with "failed to create disposable
isolation root via worktree or clone; refusing to write the bound project
root" — a platform-wide outage caused entirely by disk pressure, not code.

This sweep is conservative by construction: it only removes a checkout when
its run is provably done (terminal phase, or the run has no ledger record at
all — pruned history is expected to age out) and it has sat for at least
``min_age_seconds`` since creation, so a checkout mid-dispatch is never a
candidate even if its run row has not been written yet.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Any

from app.domain.run_state import is_terminal_phase
from app.safe_improvement.isolated_executor import (
    IsolationError,
    cleanup_isolation_root,
    read_baseline_metadata,
)

logger = logging.getLogger(__name__)

_ISOLATION_DIR_PREFIX = "axon-si-"
DEFAULT_MIN_AGE_SECONDS = 600.0


def _isolation_base_dirs() -> list[Path]:
    base = Path(tempfile.gettempdir())
    try:
        return sorted(
            entry for entry in base.iterdir()
            if entry.is_dir() and entry.name.startswith(_ISOLATION_DIR_PREFIX)
        )
    except OSError:
        return []


def _checkout_for(base_dir: Path) -> Path:
    return base_dir / "checkout"


def _parse_iso_age_seconds(created_at: str, *, now: float) -> float | None:
    from datetime import datetime, timezone

    text = str(created_at or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return now - parsed.timestamp()


def find_abandoned_isolation_roots(
    *, min_age_seconds: float = DEFAULT_MIN_AGE_SECONDS
) -> list[dict[str, Any]]:
    """Preserved/orphaned checkouts safe to remove right now.

    A checkout qualifies only when *both* hold:
      - its run is terminal, or the run_id has no ledger row at all
      - it is at least ``min_age_seconds`` old (mtime fallback when the
        baseline metadata's ``created_at`` cannot be parsed)

    Anything unreadable, mid-dispatch, or simply young is left alone —
    "not a candidate" is always the safe default here.
    """
    import time

    from app.persistence import run_store

    now = time.time()
    candidates: list[dict[str, Any]] = []
    for base_dir in _isolation_base_dirs():
        checkout = _checkout_for(base_dir)
        if not checkout.is_dir():
            continue
        try:
            meta = read_baseline_metadata(checkout)
        except (IsolationError, OSError, ValueError):
            continue
        run_id = str(meta.get("proposal_id") or "").strip()
        if not run_id:
            continue
        run = run_store.get_run(run_id)
        if run is not None and not is_terminal_phase(str(run.get("phase") or "")):
            continue

        age = _parse_iso_age_seconds(str(meta.get("created_at") or ""), now=now)
        if age is None:
            try:
                age = now - base_dir.stat().st_mtime
            except OSError:
                continue
        if age < min_age_seconds:
            continue

        candidates.append(
            {
                "run_id": run_id,
                "isolation_root": str(checkout),
                "base_dir": str(base_dir),
                "age_seconds": age,
                "run_known": run is not None,
                "bound_project_root": str(meta.get("bound_project_root") or ""),
            }
        )
    return candidates


def reap_abandoned_worker_isolations(
    *, min_age_seconds: float = DEFAULT_MIN_AGE_SECONDS
) -> list[dict[str, Any]]:
    """Remove qualifying checkouts and return what was actually cleaned."""
    cleaned: list[dict[str, Any]] = []
    for candidate in find_abandoned_isolation_roots(min_age_seconds=min_age_seconds):
        try:
            result = cleanup_isolation_root(Path(candidate["isolation_root"]))
        except Exception:  # noqa: BLE001 — one bad checkout must not stop the sweep
            logger.exception(
                "isolation reap failed for run=%s root=%s",
                candidate["run_id"],
                candidate["isolation_root"],
            )
            continue
        cleaned.append({**candidate, "cleanup": result})
    if cleaned:
        logger.info("isolation reaper removed %s abandoned worker checkout(s)", len(cleaned))
    return cleaned


__all__ = [
    "DEFAULT_MIN_AGE_SECONDS",
    "find_abandoned_isolation_roots",
    "reap_abandoned_worker_isolations",
]
