"""Load the watch FastAPI app without colliding with control-plane imports."""

from __future__ import annotations

import sys
from pathlib import Path

WATCH_ROOT = Path(__file__).resolve().parents[2] / "services" / "axon-watch"


def load_watch_app():
    cached = {
        name: module
        for name, module in sys.modules.items()
        if name == "app" or name.startswith("app.")
    }
    for name in cached:
        del sys.modules[name]

    sys.path.insert(0, str(WATCH_ROOT))
    from app.main import app as watch_app  # noqa: WPS433

    return watch_app, cached


def restore_app_modules(cached: dict[str, object]) -> None:
    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            del sys.modules[name]
    sys.modules.update(cached)
