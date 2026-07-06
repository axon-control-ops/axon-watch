"""Persist operator acknowledgements for watch inbox signals."""

from __future__ import annotations

from contextlib import contextmanager
import os

from app.persistence import watch_store_sqlite
from app.signals.iso_time import utc_now_iso

_ACKNOWLEDGED_CACHE: set[str] | None = None


def _configured_db_path() -> str | None:
    return os.environ.get("AXON_WATCH_WATCH_SERVICE_DB")


@contextmanager
def _managed_connection():
    connection = watch_store_sqlite.connect(_configured_db_path())
    try:
        yield connection
    finally:
        connection.close()


def reset_store() -> None:
    global _ACKNOWLEDGED_CACHE
    _ACKNOWLEDGED_CACHE = set()
    with _managed_connection() as connection:
        connection.execute("DELETE FROM watch_signal_acknowledgements")
        connection.commit()


def _load_acknowledged_cache() -> set[str]:
    global _ACKNOWLEDGED_CACHE
    if _ACKNOWLEDGED_CACHE is not None:
        return _ACKNOWLEDGED_CACHE

    with _managed_connection() as connection:
        rows = connection.execute(
            "SELECT signal_id FROM watch_signal_acknowledgements",
        ).fetchall()
    _ACKNOWLEDGED_CACHE = {str(row[0]) for row in rows}
    return _ACKNOWLEDGED_CACHE


def is_signal_acknowledged(signal_id: str) -> bool:
    normalized = signal_id.strip()
    if not normalized:
        return False
    return normalized in _load_acknowledged_cache()


def list_acknowledgements(*, limit: int = 50) -> dict[str, object]:
    max_limit = max(1, min(100, int(limit or 50)))
    with _managed_connection() as connection:
        count_row = connection.execute(
            "SELECT COUNT(*) FROM watch_signal_acknowledgements",
        ).fetchone()
        rows = connection.execute(
            """
            SELECT signal_id, acknowledged_at, acknowledged_by
            FROM watch_signal_acknowledgements
            ORDER BY acknowledged_at DESC, signal_id ASC
            LIMIT ?
            """,
            (max_limit,),
        ).fetchall()

    items = [
        {
            "signal_id": str(row["signal_id"]),
            "acknowledged_at": str(row["acknowledged_at"]),
            "acknowledged_by": str(row["acknowledged_by"]),
        }
        for row in rows
    ]
    return {
        "items": items,
        "count": len(items),
        "total": int(count_row[0]) if count_row is not None else 0,
    }


def acknowledge_signals(
    signal_ids: list[str],
    *,
    acknowledged_by: str = "operator",
) -> list[str]:
    normalized_ids = [signal_id.strip() for signal_id in signal_ids if signal_id.strip()]
    if not normalized_ids:
        return []

    acknowledged_at = utc_now_iso()
    actor = acknowledged_by.strip() or "operator"
    acknowledged: list[str] = []

    with _managed_connection() as connection:
        for signal_id in normalized_ids:
            if connection.execute(
                "SELECT 1 FROM watch_signal_acknowledgements WHERE signal_id = ?",
                (signal_id,),
            ).fetchone():
                acknowledged.append(signal_id)
                continue

            connection.execute(
                """
                INSERT INTO watch_signal_acknowledgements (
                    signal_id, acknowledged_at, acknowledged_by
                ) VALUES (?, ?, ?)
                """,
                (signal_id, acknowledged_at, actor),
            )
            acknowledged.append(signal_id)

        connection.commit()

    cache = _load_acknowledged_cache()
    cache.update(acknowledged)
    return acknowledged
