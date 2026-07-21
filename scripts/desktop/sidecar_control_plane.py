#!/usr/bin/env python3
"""Packaged entrypoint for the Control Plane sidecar."""

from __future__ import annotations

import os
import sys


def main() -> None:
    host = os.environ.get("AXON_WATCH_BIND_HOST", "127.0.0.1")
    port = int(os.environ.get("AXON_WATCH_CONTROL_PLANE_PORT", "8787"))
    repo = os.environ.get("AXON_WATCH_REPO_ROOT")
    if repo:
        cp_src = os.path.join(repo, "services", "control-plane")
        if cp_src not in sys.path:
            sys.path.insert(0, cp_src)
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        log_level=os.environ.get("AXON_WATCH_LOG_LEVEL", "info"),
    )


if __name__ == "__main__":
    main()
