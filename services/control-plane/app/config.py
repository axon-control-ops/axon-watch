"""Control-plane environment and deployment configuration."""

from __future__ import annotations

import os


def _watch_base_url() -> str:
    return os.environ.get(
        "AXON_WATCH_WATCH_SERVICE_BASE_URL",
        "http://127.0.0.1:8788",
    )


def _deployment_mode() -> str:
    return os.environ.get("AXON_WATCH_DEPLOYMENT_MODE", "bootstrap").strip() or "bootstrap"


def _state_dir() -> str:
    return os.environ.get("AXON_WATCH_STATE_DIR", "./.local/state")


def _public_base_url() -> str:
    return os.environ.get(
        "AXON_WATCH_PUBLIC_BASE_URL",
        "http://127.0.0.1:4173",
    ).strip() or "http://127.0.0.1:4173"


def _cors_origins() -> list[str]:
    raw = os.environ.get("AXON_WATCH_CORS_ORIGINS", "").strip()
    if raw:
        return [origin.strip() for origin in raw.split(",") if origin.strip()]
    return [
        "http://127.0.0.1:4173",
        "http://localhost:4173",
        "http://127.0.0.1:8787",
        "http://localhost:8787",
        "tauri://localhost",
        "https://tauri.localhost",
    ]
