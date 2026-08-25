"""Process-local serialization for additive SQLite feature migrations."""

from __future__ import annotations

import threading

_LOCK = threading.RLock()


def serialized_schema(function):
    def guarded(*args, **kwargs):
        with _LOCK:
            return function(*args, **kwargs)
    return guarded


__all__ = ["serialized_schema"]
