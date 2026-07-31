"""Spawn and manage a single interactive PTY shell process."""

from __future__ import annotations

import fcntl
import os
import pty
import struct
import subprocess
import termios
import threading
import time
from typing import Callable

from app.terminal.shell_invocation import (
    build_shell_command,
    build_shell_env,
    resolve_terminal_shell,
)

OutputListener = Callable[[bytes], None]
ClosedListener = Callable[[], None]


class PtyProcess:
    def __init__(
        self,
        workspace_root: str,
        *,
        session_id: str | None = None,
        preferred_shell: str | None = None,
    ) -> None:
        self.workspace_root = workspace_root
        self.session_id = session_id
        self.master_fd, slave_fd = pty.openpty()
        shell = resolve_terminal_shell(preferred_shell)
        env = build_shell_env(
            os.environ,
            workspace_root=workspace_root,
            shell=shell,
            session_id=session_id,
        )
        self.proc = subprocess.Popen(
            build_shell_command(shell),
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

        self._listener_lock = threading.Lock()
        self._output_listeners: list[OutputListener] = []
        self._closed_listeners: list[ClosedListener] = []
        self._pump_thread: threading.Thread | None = None
        self._pump_stop = threading.Event()
        self._closed_notified = False
        # Legacy asyncio reader bookkeeping (delegates to subscribe).
        self._asyncio_unsub: Callable[[], None] | None = None

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
        except OSError:
            return b""

    def poll(self) -> int | None:
        return self.proc.poll()

    def close(self) -> None:
        self._pump_stop.set()
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
        self._notify_closed()

    def subscribe(
        self,
        on_output: OutputListener,
        on_closed: ClosedListener | None = None,
    ) -> Callable[[], None]:
        """Register a fan-out listener. Starts a single pump thread when needed."""
        with self._listener_lock:
            self._output_listeners.append(on_output)
            if on_closed is not None:
                self._closed_listeners.append(on_closed)
            self._ensure_pump_locked()

        def unsubscribe() -> None:
            with self._listener_lock:
                try:
                    self._output_listeners.remove(on_output)
                except ValueError:
                    pass
                if on_closed is not None:
                    try:
                        self._closed_listeners.remove(on_closed)
                    except ValueError:
                        pass

        return unsubscribe

    def attach_reader(self, loop, on_output: OutputListener, on_closed: ClosedListener) -> None:
        """Attach asyncio-friendly listeners via the shared pump (thread-safe)."""

        def _out(chunk: bytes) -> None:
            loop.call_soon_threadsafe(on_output, chunk)

        def _closed() -> None:
            loop.call_soon_threadsafe(on_closed)

        if self._asyncio_unsub is not None:
            self._asyncio_unsub()
        self._asyncio_unsub = self.subscribe(_out, _closed)

    def detach_reader(self, loop) -> None:  # noqa: ARG002 — API parity
        if self._asyncio_unsub is not None:
            self._asyncio_unsub()
            self._asyncio_unsub = None

    def _ensure_pump_locked(self) -> None:
        if self._pump_thread is not None and self._pump_thread.is_alive():
            return
        self._pump_stop.clear()
        self._closed_notified = False
        thread = threading.Thread(
            target=self._pump_loop,
            name=f"pty-pump-{self.session_id or 'shell'}",
            daemon=True,
        )
        self._pump_thread = thread
        thread.start()

    def _pump_loop(self) -> None:
        while not self._pump_stop.is_set():
            chunk = self.read_available()
            if chunk:
                with self._listener_lock:
                    listeners = list(self._output_listeners)
                for listener in listeners:
                    try:
                        listener(chunk)
                    except Exception:  # noqa: BLE001 — never kill the pump
                        continue
                continue
            if self.poll() is not None:
                self._notify_closed()
                return
            time.sleep(0.02)

    def _notify_closed(self) -> None:
        with self._listener_lock:
            if self._closed_notified:
                return
            self._closed_notified = True
            closed = list(self._closed_listeners)
        for listener in closed:
            try:
                listener()
            except Exception:  # noqa: BLE001
                continue
