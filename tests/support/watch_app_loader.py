"""Load the watch FastAPI app without colliding with control-plane imports."""

from __future__ import annotations

import sys
from pathlib import Path

WATCH_ROOT = Path(__file__).resolve().parents[2] / "services" / "axon-watch"


def prepare_watch_imports() -> dict[str, object]:
    """Clear cached ``app`` modules and prioritize axon-watch on ``sys.path``."""
    cached = {
        name: module
        for name, module in sys.modules.items()
        if name == "app" or name.startswith("app.")
    }
    for name in cached:
        del sys.modules[name]

    watch_path = str(WATCH_ROOT)
    while watch_path in sys.path:
        sys.path.remove(watch_path)
    sys.path.insert(0, watch_path)
    return cached


def load_watch_app():
    cached = {
        name: module
        for name, module in sys.modules.items()
        if name == "app" or name.startswith("app.")
    }
    for name in cached:
        del sys.modules[name]

    sys.path.insert(0, str(WATCH_ROOT))
    try:
        from app.main import app as watch_app  # noqa: WPS433
    except Exception:
        restore_app_modules(cached)
        raise
    finally:
        sys.path.remove(str(WATCH_ROOT))

    return watch_app, cached


def restore_app_modules(cached: dict[str, object]) -> None:
    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            del sys.modules[name]
    sys.modules.update(cached)
