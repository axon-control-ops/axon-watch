"""Track in-flight CLI runtime subprocesses so operator stop can cancel execution."""

from __future__ import annotations

import subprocess
import threading
from typing import Any

from app.cli_runtime.agent_process_scope import (
    agent_scope_unit_from_wrapped_command,
    stop_agent_scope,
)

_lock = threading.Lock()
_processes: dict[str, subprocess.Popen[Any]] = {}


def register(run_id: str, proc: subprocess.Popen[Any]) -> None:
    clean_id = str(run_id or "").strip()
    if not clean_id:
        return
    with _lock:
        _processes[clean_id] = proc


def unregister(run_id: str) -> None:
    clean_id = str(run_id or "").strip()
    if not clean_id:
        return
    with _lock:
        _processes.pop(clean_id, None)


def is_registered(run_id: str) -> bool:
    clean_id = str(run_id or "").strip()
    if not clean_id:
        return False
    with _lock:
        return clean_id in _processes


def terminate(run_id: str) -> bool:
    clean_id = str(run_id or "").strip()
    if not clean_id:
        return False
    with _lock:
        proc = _processes.get(clean_id)
    if proc is None:
        return False
    if proc.poll() is None:
        scope_unit = agent_scope_unit_from_wrapped_command(proc.args)
        if scope_unit:
            stop_agent_scope(scope_unit)
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
    unregister(clean_id)
    return True


def clear_registry() -> None:
    with _lock:
        _processes.clear()
