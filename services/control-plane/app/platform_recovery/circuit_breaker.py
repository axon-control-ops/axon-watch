"""Circuit breakers for external dependencies."""

from __future__ import annotations

from typing import Any

from app.platform_recovery.states import CIRCUIT_STATES
from app.platform_recovery.store import managed_connection, utc_now_iso

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


def record_success(name: str) -> dict[str, Any]:
    now = utc_now_iso()
    current = get_circuit(name)
    state = "CLOSED"
    with managed_connection() as conn:
        conn.execute(
            """
            INSERT INTO circuit_breakers (name, state, failure_count, last_success_at)
            VALUES (?, ?, 0, ?)
            ON CONFLICT(name) DO UPDATE SET
                state=excluded.state,
                failure_count=0,
                last_success_at=excluded.last_success_at
            """,
            (name, state, now),
        )
        conn.commit()
    current.update({"state": state, "failure_count": 0, "last_success_at": now})
    return current


def record_failure(name: str) -> dict[str, Any]:
    now = utc_now_iso()
    current = get_circuit(name)
    count = int(current.get("failure_count") or 0) + 1
    state = "OPEN" if count >= _OPEN_AFTER else "CLOSED"
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


def allow_request(name: str) -> bool:
    return str(get_circuit(name).get("state") or "CLOSED") != "OPEN"
