"""Append NDJSON evidence lines for Debug-mode instrumentation."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any


def _candidate_roots() -> list[Path]:
    here = Path(__file__).resolve()
    # services/control-plane/app -> axon-watch repo root
    axon_watch_root = here.parents[3]
    roots = [axon_watch_root]
    # Sibling axon-local (Cursor project root for this debug session)
    sibling_local = axon_watch_root.parent / "axon-local"
    if sibling_local.is_dir():
        roots.append(sibling_local)
    return roots


def append_debug_session_log(
    *,
    hypothesis_id: str,
    location: str,
    message: str,
    data: dict[str, Any] | None = None,
) -> None:
    if os.environ.get("AXON_DEBUG_SESSION_LOG") != "1":
        return

    payload = {
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data or {},
        "timestamp": int(time.time() * 1000),
    }
    line = json.dumps(payload, ensure_ascii=True) + "\n"
    for root in _candidate_roots():
        axon_dir = root / ".axon"
        try:
            axon_dir.mkdir(parents=True, exist_ok=True)
            with (axon_dir / "debug-session.ndjson").open("a", encoding="utf-8") as handle:
                handle.write(line)
        except OSError:
            continue
