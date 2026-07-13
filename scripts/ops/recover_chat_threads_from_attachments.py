#!/usr/bin/env python3
"""Restore wiped chat threads/messages from surviving chat_attachments rows.

The Axon-X control-plane DB had chat_threads/chat_messages deleted while
attachment rows (and files) remained. Message bodies are not recoverable from
zeroed freelist pages; this rebuilds thread shells and stub messages so history
tabs and image attachments reappear.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = REPO_ROOT / ".local/state/control-plane.sqlite3"

RECOVERY_NOTE = (
    "[Recovered after chat-store wipe — original message text is unavailable. "
    "Attachments from this turn were restored.]"
)


def recover(db_path: Path, *, dry_run: bool = False) -> dict[str, int]:
    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    try:
        attachments = connection.execute(
            """
            SELECT attachment_id, workspace_id, message_id, thread_id, filename, created_at
            FROM chat_attachments
            WHERE thread_id IS NOT NULL AND message_id IS NOT NULL
            ORDER BY created_at ASC, attachment_id ASC
            """
        ).fetchall()

        threads: dict[str, dict[str, object]] = {}
        messages: dict[str, dict[str, object]] = {}
        for row in attachments:
            thread_id = str(row["thread_id"])
            message_id = str(row["message_id"])
            workspace_id = str(row["workspace_id"])
            created_at = str(row["created_at"])
            thread = threads.setdefault(
                thread_id,
                {
                    "thread_id": thread_id,
                    "workspace_id": workspace_id,
                    "created_at": created_at,
                    "updated_at": created_at,
                },
            )
            thread["updated_at"] = max(str(thread["updated_at"]), created_at)
            thread["created_at"] = min(str(thread["created_at"]), created_at)

            role = "agent" if message_id.startswith("message_agent_") else "operator"
            message = messages.setdefault(
                message_id,
                {
                    "message_id": message_id,
                    "thread_id": thread_id,
                    "workspace_id": workspace_id,
                    "run_id": None,
                    "role": role,
                    "content": RECOVERY_NOTE,
                    "created_at": created_at,
                },
            )
            message["created_at"] = min(str(message["created_at"]), created_at)

        inserted_threads = 0
        inserted_messages = 0
        if dry_run:
            return {
                "attachments": len(attachments),
                "threads": len(threads),
                "messages": len(messages),
                "inserted_threads": 0,
                "inserted_messages": 0,
            }

        for thread in threads.values():
            existing = connection.execute(
                "SELECT 1 FROM chat_threads WHERE thread_id = ?",
                (thread["thread_id"],),
            ).fetchone()
            if existing:
                continue
            connection.execute(
                """
                INSERT INTO chat_threads (
                    thread_id, workspace_id, run_id, thread_kind, created_at, updated_at
                ) VALUES (?, ?, NULL, 'ide', ?, ?)
                """,
                (
                    thread["thread_id"],
                    thread["workspace_id"],
                    thread["created_at"],
                    thread["updated_at"],
                ),
            )
            inserted_threads += 1

        for message in messages.values():
            existing = connection.execute(
                "SELECT 1 FROM chat_messages WHERE message_id = ?",
                (message["message_id"],),
            ).fetchone()
            if existing:
                continue
            connection.execute(
                """
                INSERT INTO chat_messages (
                    message_id, thread_id, workspace_id, run_id, role, content, created_at
                ) VALUES (?, ?, ?, NULL, ?, ?, ?)
                """,
                (
                    message["message_id"],
                    message["thread_id"],
                    message["workspace_id"],
                    message["role"],
                    message["content"],
                    message["created_at"],
                ),
            )
            inserted_messages += 1

        connection.commit()
        return {
            "attachments": len(attachments),
            "threads": len(threads),
            "messages": len(messages),
            "inserted_threads": inserted_threads,
            "inserted_messages": inserted_messages,
        }
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB,
        help=f"control-plane sqlite path (default: {DEFAULT_DB})",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not args.db.exists():
        print(f"database not found: {args.db}", file=sys.stderr)
        return 1
    result = recover(args.db, dry_run=args.dry_run)
    prefix = "dry-run" if args.dry_run else "recovered"
    print(
        f"{prefix}: attachments={result['attachments']} "
        f"threads={result['threads']} messages={result['messages']} "
        f"inserted_threads={result['inserted_threads']} "
        f"inserted_messages={result['inserted_messages']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
