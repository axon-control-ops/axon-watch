"""Spawn and manage a single interactive PTY shell process."""

from __future__ import annotations

import fcntl
import os
import pty
import struct
import subprocess
import termios
from typing import Callable


class PtyProcess:
    def __init__(self, workspace_root: str) -> None:
        self.workspace_root = workspace_root
        self.master_fd, slave_fd = pty.openpty()
        shell = os.environ.get("AXON_WATCH_TERMINAL_SHELL", os.environ.get("SHELL", "/bin/bash"))
        env = os.environ.copy()
        env.setdefault("TERM", "xterm-256color")
        env["PWD"] = workspace_root
        self.proc = subprocess.Popen(
            [shell],
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            cwd=workspace_root,
            env=env,
            preexec_fn=os.setsid,
            close_fds=True,
        )
        os.close(slave_fd)
        flags = fcntl.fcntl(self.master_fd, fcntl.F_GETFL)
        fcntl.fcntl(self.master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

    def resize(self, cols: int, rows: int) -> None:
        cols = max(1, int(cols))
        rows = max(1, int(rows))
        winsize = struct.pack("HHHH", rows, cols, 0, 0)
        fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, winsize)

    def write(self, data: bytes) -> None:
        if not data:
            return
        os.write(self.master_fd, data)

    def read_available(self, size: int = 4096) -> bytes:
        try:
            return os.read(self.master_fd, size)
        except BlockingIOError:
            return b""

    def poll(self) -> int | None:
        return self.proc.poll()

    def close(self) -> None:
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=2)
        try:
            os.close(self.master_fd)
        except OSError:
            pass

    def attach_reader(self, loop, on_output: Callable[[bytes], None], on_closed: Callable[[], None]) -> None:
        def _read_ready() -> None:
            while True:
                chunk = self.read_available()
                if chunk:
                    on_output(chunk)
                    continue
                if self.poll() is not None:
                    on_closed()
                    return
                break

        loop.add_reader(self.master_fd, _read_ready)

    def detach_reader(self, loop) -> None:
        loop.remove_reader(self.master_fd)
