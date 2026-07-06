"""Control-plane operator data routes (read-only, no secret values)."""

from __future__ import annotations

from typing import Any

from app.data.snapshot import operator_data_snapshot


def get_data_snapshot(*, limit: int = 50) -> dict[str, Any]:
    return {"data": operator_data_snapshot(limit=limit)}


def get_data_export(*, limit: int = 50) -> dict[str, Any]:
    return get_data_snapshot(limit=limit)
