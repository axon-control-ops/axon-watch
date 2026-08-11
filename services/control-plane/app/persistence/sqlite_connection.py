"""SQLite connection ownership helpers."""

from __future__ import annotations

import sqlite3
from types import TracebackType
from typing import Self


class ManagedConnection(sqlite3.Connection):
    """Commit or roll back a context transaction, then release its handle."""

    def __enter__(self) -> Self:
        return super().__enter__()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        try:
            return bool(super().__exit__(exc_type, exc_value, traceback))
        finally:
            self.close()

    def __del__(self) -> None:
        # Some long-lived in-memory stores are replaced during test/module
        # reloads. Release their handles before sqlite3's warning-only finalizer.
        try:
            self.close()
        except sqlite3.Error:
            pass
