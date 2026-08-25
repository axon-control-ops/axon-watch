"""Host process inventory. Never kill blindly — report ownership first."""

from __future__ import annotations

import os
import socket
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WATCHED_PORTS = (4173, 8787, 8788, 5173)
SERVICE_NAMES = {
    4173: "console-web",
    8787: "control-plane",
    8788: "axon-watch",
    5173: "vite-dev",
}


def _proc_field(pid: int, name: str) -> str:
    path = Path(f"/proc/{pid}/{name}")
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return ""


def _cmdline(pid: int) -> str:
    raw = _proc_field(pid, "cmdline")
    return raw.replace("\x00", " ").strip()


def _start_time(pid: int) -> str:
    stat = _proc_field(pid, "stat")
    if not stat:
        return ""
    try:
        mtime = Path(f"/proc/{pid}").stat().st_mtime
    except OSError:
        return ""
    return datetime.fromtimestamp(mtime, tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _cwd(pid: int) -> str:
    try:
        return str(Path(f"/proc/{pid}/cwd").resolve())
    except OSError:
        return ""


def _port_pid(port: int) -> int | None:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.2):
            pass
    except OSError:
        return None
    # Listening does not yield PID via connect. Scan /proc/*/fd for socket inodes is heavy;
    # prefer ss when present, else mark unknown-but-listening.
    for pid_dir in Path("/proc").iterdir():
        if not pid_dir.name.isdigit():
            continue
        fd_dir = pid_dir / "fd"
        if not fd_dir.is_dir():
            continue
        try:
            for fd in fd_dir.iterdir():
                target = os.readlink(fd)
                if f":{port}" in target:
                    return int(pid_dir.name)
        except OSError:
            continue
    return None


def _safe_to_terminate(pid: int, repo_root: Path) -> bool:
    cwd = _cwd(pid)
    cmdline = _cmdline(pid)
    if not cwd and not cmdline:
        return False
    repo = str(repo_root)
    if cwd.startswith(repo) and any(token in cmdline for token in ("pytest", "unittest", "vitest")):
        return True
    if ".local/pids" in cmdline:
        return False
    cgroup = _proc_field(pid, "cgroup")
    if ".service" in cgroup:
        return False
    return False


def inspect_processes(*, repo_root: str | None = None) -> list[dict[str, Any]]:
    root = Path(repo_root or Path(__file__).resolve().parents[4])
    rows: list[dict[str, Any]] = []
    seen: set[int] = set()
    for port in WATCHED_PORTS:
        pid = _port_pid(port)
        listening = pid is not None or _port_listening(port)
        row = {
            "process": SERVICE_NAMES.get(port, f"port-{port}"),
            "pid": pid,
            "port": port,
            "owner": (
                _cmdline(pid)[:180]
                if pid
                else "listener pid unavailable"
                if listening
                else "not listening"
            ),
            "start_time": _start_time(pid) if pid else "",
            "workspace": _cwd(pid) if pid else "",
            "state": "listening" if listening else "idle",
            "safe_to_terminate": bool(pid and _safe_to_terminate(pid, root)),
        }
        if pid:
            seen.add(pid)
        rows.append(row)
    rows.extend(_scan_test_processes(root, seen))
    return rows


def _port_listening(port: int) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.2)
    try:
        return sock.connect_ex(("127.0.0.1", port)) == 0
    finally:
        sock.close()


def _scan_test_processes(root: Path, seen: set[int]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    repo = str(root)
    for pid_dir in Path("/proc").iterdir():
        if not pid_dir.name.isdigit():
            continue
        pid = int(pid_dir.name)
        if pid in seen:
            continue
        cmdline = _cmdline(pid)
        if not cmdline:
            continue
        if not any(token in cmdline for token in ("pytest", "unittest", "vitest", "npm test")):
            continue
        cwd = _cwd(pid)
        if cwd and not cwd.startswith(repo) and repo not in cmdline:
            continue
        rows.append(
            {
                "process": "test",
                "pid": pid,
                "port": None,
                "owner": cmdline[:180],
                "start_time": _start_time(pid),
                "workspace": cwd,
                "state": "running",
                "safe_to_terminate": _safe_to_terminate(pid, root),
            }
        )
    return rows
