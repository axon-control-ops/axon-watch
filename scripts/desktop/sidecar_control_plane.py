#!/usr/bin/env python3
"""Packaged entrypoint for the Control Plane sidecar."""

from __future__ import annotations

import os
import sys


def _prepare_import_path() -> None:
    if getattr(sys, "frozen", False):
        return
    repo = os.environ.get("AXON_WATCH_REPO_ROOT")
    if not repo:
        return
    cp_src = os.path.join(repo, "services", "control-plane")
    if cp_src not in sys.path:
        sys.path.insert(0, cp_src)


def main() -> None:
    _prepare_import_path()
    host = os.environ.get("AXON_WATCH_BIND_HOST", "127.0.0.1")
    port = int(os.environ.get("AXON_WATCH_CONTROL_PLANE_PORT", "8787"))
    # Ensure PyInstaller traces the FastAPI app package.
    import app.main  # noqa: F401
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        log_level=os.environ.get("AXON_WATCH_LOG_LEVEL", "info"),
    )


if __name__ == "__main__":
    main()
