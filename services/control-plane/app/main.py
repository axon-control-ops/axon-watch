"""Minimal FastAPI shell for the control-plane bootstrap slice."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth import MutatingAuthMiddleware
from app.bootstrap import control_plane_lifespan, probe_all_connectors
from app.config import _cors_origins
from app.routes import register_routes

app = FastAPI(
    title="Axon-X Control Plane",
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
    lifespan=control_plane_lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["*"],
)
# Outer middleware runs first on the request; auth must see mutating methods.
app.add_middleware(MutatingAuthMiddleware)
register_routes(app)
# Re-export for tests/support/stable_connector_probe.py patch sites.
__all__ = ["app", "probe_all_connectors"]
