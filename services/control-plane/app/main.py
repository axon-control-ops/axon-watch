"""Minimal FastAPI shell for the control-plane bootstrap slice."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.adapters.watch_client import fetch_watch_delivery_receipts
from app.cli_runtime.routes import get_runtime_mcp_tools, get_runtime_status
from app.config import _cors_origins
from app.data.routes import get_data_export, get_data_snapshot
from app.routes import register_routes

app = FastAPI(
    title="Axon-X Control Plane",
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["*"],
)

register_routes(app)


def probe_all_connectors() -> list[dict[str, object]]:
    """Compatibility stub for tests/support/stable_connector_probe.py patch sites."""
    return []
