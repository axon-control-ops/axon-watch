"""Circuit breakers for external dependencies."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from app.platform_recovery.states import CIRCUIT_STATES
from app.platform_recovery.store import managed_connection

KNOWN_CIRCUITS = (
    "provider.ai",
    "provider.github",
    "provider.ci",
    "watch",
    "database",
    "filesystem.worktree",
    "network",
)

_OPEN_AFTER = 3
_HALF_OPEN_AFTER_SECONDS = 60
Clock = Callable[[], datetime]


def _row(name: str, **fields: Any) -> dict[str, Any]:
    payload = {
        "name": name,
        "state": "CLOSED",
        "failure_count": 0,
        "opened_at": None,
        "last_failure_at": None,
        "last_success_at": None,
    }
    payload.update(fields)
    if payload["state"] not in CIRCUIT_STATES:
        payload["state"] = "CLOSED"
    return payload


def _utc_now(clock: Clock | None = None) -> datetime:
    now = clock() if clock is not None else datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return now.astimezone(timezone.utc).replace(microsecond=0)


def _iso(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _parse_iso(value: object) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _cooldown_elapsed(current: dict[str, Any], now: datetime) -> bool:
    opened_at = _parse_iso(current.get("opened_at") or current.get("last_failure_at"))
    if opened_at is None:
        return False
    return (now - opened_at).total_seconds() >= _HALF_OPEN_AFTER_SECONDS


def get_circuit(name: str) -> dict[str, Any]:
    cleaned = str(name or "").strip()
    with managed_connection() as conn:
        row = conn.execute(
            "SELECT * FROM circuit_breakers WHERE name = ?",
            (cleaned,),
        ).fetchone()
    if row is None:
        return _row(cleaned)
    return _row(
        row["name"],
        state=row["state"],
        failure_count=int(row["failure_count"] or 0),
        opened_at=row["opened_at"],
        last_failure_at=row["last_failure_at"],
        last_success_at=row["last_success_at"],
    )


def list_circuits() -> list[dict[str, Any]]:
    known = {name: get_circuit(name) for name in KNOWN_CIRCUITS}
    with managed_connection() as conn:
        rows = conn.execute("SELECT name FROM circuit_breakers").fetchall()
    for row in rows:
        name = str(row["name"])
        if name not in known:
            known[name] = get_circuit(name)
    return [known[name] for name in sorted(known)]


def record_success(name: str, *, clock: Clock | None = None) -> dict[str, Any]:
    now = _iso(_utc_now(clock))
    current = get_circuit(name)
    state = "CLOSED"
    with managed_connection() as conn:
        conn.execute(
            """
            INSERT INTO circuit_breakers (name, state, failure_count, opened_at, last_success_at)
            VALUES (?, ?, 0, NULL, ?)
            ON CONFLICT(name) DO UPDATE SET
                state=excluded.state,
                failure_count=0,
                opened_at=NULL,
                last_success_at=excluded.last_success_at
            """,
            (name, state, now),
        )
        conn.commit()
    current.update({"state": state, "failure_count": 0, "opened_at": None, "last_success_at": now})
    return current


def record_failure(name: str, *, clock: Clock | None = None) -> dict[str, Any]:
    now = _iso(_utc_now(clock))
    current = get_circuit(name)
    count = int(current.get("failure_count") or 0) + 1
    state = "OPEN" if current.get("state") == "HALF_OPEN" or count >= _OPEN_AFTER else "CLOSED"
    opened_at = now if state == "OPEN" else current.get("opened_at")
    with managed_connection() as conn:
        conn.execute(
            """
            INSERT INTO circuit_breakers (
                name, state, failure_count, opened_at, last_failure_at
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                state=excluded.state,
                failure_count=excluded.failure_count,
                opened_at=excluded.opened_at,
                last_failure_at=excluded.last_failure_at
            """,
            (name, state, count, opened_at, now),
        )
        conn.commit()
    current.update(
        {
            "state": state,
            "failure_count": count,
            "opened_at": opened_at,
            "last_failure_at": now,
        }
    )
    return current


def allow_request(name: str, *, clock: Clock | None = None) -> bool:
    current = get_circuit(name)
    state = str(current.get("state") or "CLOSED")
    if state == "CLOSED":
        return True
    if state == "HALF_OPEN":
        return False
    if state != "OPEN" or not _cooldown_elapsed(current, _utc_now(clock)):
        return False

    with managed_connection() as conn:
        conn.execute(
            """
            UPDATE circuit_breakers
            SET state = ?
            WHERE name = ? AND state = ?
            """,
            ("HALF_OPEN", name, "OPEN"),
        )
        conn.commit()
    return True
