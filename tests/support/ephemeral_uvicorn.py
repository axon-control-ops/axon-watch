"""Start a FastAPI app on an ephemeral port for cross-service integration tests."""

from __future__ import annotations

import socket
import threading
import time
from urllib.error import URLError
from urllib.request import urlopen

import uvicorn


def pick_free_port(host: str = "127.0.0.1") -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


class EphemeralUvicorn:
    def __init__(self, app, host: str = "127.0.0.1", port: int | None = None) -> None:
        self.host = host
        self.port = port or pick_free_port(host)
        self.base_url = f"http://{self.host}:{self.port}"
        self._config = uvicorn.Config(app, host=self.host, port=self.port, log_level="error")
        self._server = uvicorn.Server(self._config)
        self._thread = threading.Thread(target=self._server.run, daemon=True, name="ephemeral-uvicorn")

    def start(self, health_path: str, timeout_seconds: float = 5.0) -> None:
        self._thread.start()
        deadline = time.monotonic() + timeout_seconds
        health_url = f"{self.base_url}{health_path}"

        while time.monotonic() < deadline:
            try:
                with urlopen(health_url, timeout=0.25) as response:
                    if response.status == 200:
                        return
            except (URLError, TimeoutError, OSError):
                time.sleep(0.05)

        raise RuntimeError(f"ephemeral server did not become ready: {health_url}")

    def stop(self) -> None:
        self._server.should_exit = True
        self._thread.join(timeout=3.0)
