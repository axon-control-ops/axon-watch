"""Minimal FastAPI shell for the control-plane bootstrap slice."""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.runtime_summary import build_runtime_summary


def _watch_base_url() -> str:
    return os.environ.get(
        "AXON_WATCH_WATCH_SERVICE_BASE_URL",
        "http://127.0.0.1:8788",
    )


app = FastAPI(
    title="Axon-Watch Control Plane",
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:4173",
        "http://localhost:4173",
    ],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {
        "service": "control-plane",
        "status": "ok",
        "mode": "bootstrap",
    }


@app.get("/api/readiness")
def readiness() -> dict[str, object]:
    return {
        "service": "control-plane",
        "status": "ready",
        "mode": "bootstrap",
        "watch_base_url": _watch_base_url(),
    }


@app.get("/api/runtime/summary")
def runtime_summary() -> dict[str, object]:
    return build_runtime_summary()
