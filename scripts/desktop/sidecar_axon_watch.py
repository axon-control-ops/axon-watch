#!/usr/bin/env python3
"""Packaged entrypoint for the Axon Watch sidecar."""

from __future__ import annotations

import os
import sys


def _prepare_import_path() -> None:
    if getattr(sys, "frozen", False):
        return
    repo = os.environ.get("AXON_WATCH_REPO_ROOT")
    if not repo:
        return
    watch_src = os.path.join(repo, "services", "axon-watch")
    if watch_src not in sys.path:
        sys.path.insert(0, watch_src)


def main() -> None:
    _prepare_import_path()
    host = os.environ.get("AXON_WATCH_BIND_HOST", "127.0.0.1")
    port = int(os.environ.get("AXON_WATCH_WATCH_SERVICE_PORT", "8788"))
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
