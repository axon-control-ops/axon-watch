"""Lightweight append-only auth/vault audit receipts for Gate 2 evidence."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.auth.identity import get_request_identity
from app.config import _state_dir


def _audit_path() -> Path:
    override = os.environ.get("AXON_WATCH_AUTH_AUDIT_LOG", "").strip()
    if override:
        return Path(override)
    return Path(_state_dir()) / "auth-audit.ndjson"


def append_auth_audit(
    *,
    event_type: str,
    summary: str,
    success: bool,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    record = {
        "ts": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "event_type": str(event_type or "").strip() or "auth_event",
        "summary": " ".join(str(summary or "").split()),
        "success": bool(success),
        "identity": get_request_identity(),
    }
    if extra:
        record["extra"] = extra
    path = _audit_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
    return record
