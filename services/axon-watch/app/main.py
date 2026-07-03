"""Minimal FastAPI shell for the watch service bootstrap slice."""

from __future__ import annotations

import os

from fastapi import FastAPI


def _state_dir() -> str:
    return os.environ.get("AXON_WATCH_STATE_DIR", "./.local/state")


app = FastAPI(
    title="Axon-Watch Service",
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
)


@app.get("/internal/watch/health")
def health() -> dict[str, str]:
    return {
        "service": "axon-watch",
        "status": "ok",
        "mode": "bootstrap",
    }


@app.get("/internal/watch/readiness")
def readiness() -> dict[str, object]:
    return {
        "service": "axon-watch",
        "status": "ready",
        "mode": "bootstrap",
        # Keep readiness limited to owned bootstrap wiring only.
        "state_dir": _state_dir(),
    }
