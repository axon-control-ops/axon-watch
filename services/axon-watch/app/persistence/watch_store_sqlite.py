"""SQLite primitives for persisted axon-watch commands, events, and receipts."""

from __future__ import annotations

import sqlite3
from pathlib import Path

_DEFAULT_DB = "./.local/state/axon-watch.sqlite3"
MAX_EVENTS = 200
MAX_RECEIPTS = 200


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def resolve_db_path(configured_path: str | None) -> Path:
    raw_path = (configured_path or _DEFAULT_DB).strip() or _DEFAULT_DB
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return (_repo_root() / path).resolve()


def connect(configured_path: str | None) -> sqlite3.Connection:
    db_path = resolve_db_path(configured_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    ensure_schema(connection)
    return connection


def ensure_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS watch_commands (
            command_id TEXT PRIMARY KEY,
            updated_at TEXT NOT NULL,
            record_json TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_watch_commands_updated_at
            ON watch_commands(updated_at DESC, command_id ASC);

        CREATE TABLE IF NOT EXISTS watch_events (
            event_id TEXT PRIMARY KEY,
            sequence INTEGER NOT NULL UNIQUE,
            occurred_at TEXT NOT NULL,
            record_json TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_watch_events_sequence
            ON watch_events(sequence DESC);

        CREATE TABLE IF NOT EXISTS watch_delivery_receipts (
            receipt_id TEXT PRIMARY KEY,
            signal_id TEXT NOT NULL,
            channel TEXT NOT NULL,
            attempted_at TEXT NOT NULL,
            result TEXT NOT NULL,
            record_json TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_watch_delivery_receipts_attempted_at
            ON watch_delivery_receipts(attempted_at DESC, receipt_id ASC);

        CREATE INDEX IF NOT EXISTS idx_watch_delivery_receipts_signal
            ON watch_delivery_receipts(signal_id, attempted_at DESC);

        CREATE TABLE IF NOT EXISTS watch_delivery_dedupe (
            dedupe_key TEXT PRIMARY KEY
        );

        CREATE TABLE IF NOT EXISTS watch_signal_acknowledgements (
            signal_id TEXT PRIMARY KEY,
            acknowledged_at TEXT NOT NULL,
            acknowledged_by TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_watch_signal_acknowledgements_at
            ON watch_signal_acknowledgements(acknowledged_at DESC);
        """
    )
