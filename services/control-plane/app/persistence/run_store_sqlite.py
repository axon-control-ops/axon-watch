"""SQLite primitives for persisted control-plane run state."""

from __future__ import annotations

import sqlite3
from pathlib import Path

_DEFAULT_DB = "./.local/state/control-plane.sqlite3"


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
        CREATE TABLE IF NOT EXISTS runs (
            run_id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            lane_id TEXT NOT NULL,
            mode TEXT NOT NULL,
            status TEXT NOT NULL,
            phase TEXT NOT NULL,
            summary TEXT NOT NULL,
            detail TEXT NOT NULL,
            started_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            ended_at TEXT,
            can_stop INTEGER NOT NULL,
            can_resume INTEGER NOT NULL,
            can_approve INTEGER NOT NULL,
            can_review INTEGER NOT NULL,
            current_step TEXT,
            history_ref TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_runs_updated_at
            ON runs(updated_at DESC, run_id ASC);

        CREATE INDEX IF NOT EXISTS idx_runs_phase
            ON runs(phase);

        CREATE TABLE IF NOT EXISTS chat_threads (
            thread_id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            run_id TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS chat_messages (
            message_id TEXT PRIMARY KEY,
            thread_id TEXT NOT NULL,
            workspace_id TEXT NOT NULL,
            run_id TEXT,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(thread_id) REFERENCES chat_threads(thread_id)
        );

        CREATE INDEX IF NOT EXISTS idx_chat_threads_workspace
            ON chat_threads(workspace_id, updated_at DESC);

        CREATE INDEX IF NOT EXISTS idx_chat_messages_thread
            ON chat_messages(thread_id, created_at ASC, message_id ASC);

        CREATE TABLE IF NOT EXISTS run_history (
            history_ref TEXT NOT NULL,
            sequence INTEGER NOT NULL,
            transition_json TEXT NOT NULL,
            PRIMARY KEY(history_ref, sequence)
        );

        CREATE TABLE IF NOT EXISTS workspace_handoffs (
            handoff_id TEXT PRIMARY KEY,
            source_workspace_id TEXT NOT NULL,
            target_workspace_id TEXT NOT NULL,
            task TEXT NOT NULL,
            reason TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'recorded',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_workspace_handoffs_source
            ON workspace_handoffs(source_workspace_id, created_at DESC);

        CREATE INDEX IF NOT EXISTS idx_workspace_handoffs_target
            ON workspace_handoffs(target_workspace_id, created_at DESC);

        CREATE TABLE IF NOT EXISTS operator_presence_settings (
            settings_key TEXT PRIMARY KEY,
            settings_json TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """
    )
    _ensure_chat_thread_kind_column(connection)
    _ensure_chat_attachments_table(connection)


def _ensure_chat_attachments_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_attachments (
            attachment_id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            message_id TEXT,
            thread_id TEXT,
            filename TEXT NOT NULL,
            mime_type TEXT NOT NULL,
            storage_path TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_chat_attachments_message
            ON chat_attachments(message_id, created_at ASC)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_chat_attachments_workspace
            ON chat_attachments(workspace_id, created_at DESC)
        """
    )
    connection.commit()


def _ensure_chat_thread_kind_column(connection: sqlite3.Connection) -> None:
    columns = {
        str(row[1])
        for row in connection.execute("PRAGMA table_info(chat_threads)").fetchall()
    }
    if "thread_kind" in columns:
        return
    connection.execute(
        "ALTER TABLE chat_threads ADD COLUMN thread_kind TEXT NOT NULL DEFAULT 'operator'"
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_chat_threads_workspace_kind
            ON chat_threads(workspace_id, thread_kind, updated_at DESC)
        """
    )
    connection.commit()
