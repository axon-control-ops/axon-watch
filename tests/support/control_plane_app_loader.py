"""Load control-plane modules without colliding with axon-watch imports."""

from __future__ import annotations

import sys
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[2] / "services" / "control-plane"


def prepare_control_plane_imports() -> dict[str, object]:
    """Clear cached ``app`` modules and prioritize control-plane on ``sys.path``."""
    cached = {
        name: module
        for name, module in sys.modules.items()
        if name == "app" or name.startswith("app.")
    }
    for name in cached:
        del sys.modules[name]

    cp_path = str(CONTROL_PLANE_ROOT)
    while cp_path in sys.path:
        sys.path.remove(cp_path)
    sys.path.insert(0, cp_path)
    return cached


def load_control_plane_app():
    """Return a fresh control-plane FastAPI app after clearing stale ``app`` imports.

    TestClient must bind to this app *after* ``prepare_control_plane_imports()``;
    reusing a module-level ``app`` leaves route handlers pointing at deleted modules,
    so ``fetch_watch_inbox`` mocks miss and tests hit the live watch inbox.
    """
    prepare_control_plane_imports()
    from app.main import app

    return app
