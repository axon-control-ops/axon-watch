"""Load the watch FastAPI app without colliding with control-plane imports."""

from __future__ import annotations

import sys
from collections.abc import Callable
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


def snapshot_app_modules() -> dict[str, object]:
    """Capture the currently loaded ``app`` package tree."""
    return {
        name: module
        for name, module in sys.modules.items()
        if name == "app" or name.startswith("app.")
    }


def wrap_inprocess_watch_app(watch_app, watch_modules: dict[str, object]):
    """Swap in watch ``app`` imports while an in-process ASGI server handles a request."""
    async def asgi(scope, receive, send):
        saved = snapshot_app_modules()
        for name in saved:
            del sys.modules[name]
        sys.modules.update(watch_modules)
        try:
            await watch_app(scope, receive, send)
        finally:
            active = snapshot_app_modules()
            for name in active:
                del sys.modules[name]
            sys.modules.update(saved)

    return asgi


def load_control_plane_watch_pair(
    *,
    on_watch_loaded: Callable[[], None] | None = None,
):
    """Load watch ASGI with module isolation; restore control-plane imports for TestClient.

    ``on_watch_loaded`` runs while watch ``app`` modules are still active — use for
    ephemeral store resets or probe patches that import from watch packages.
    """
    watch_app, control_plane_modules = load_watch_app()
    if on_watch_loaded is not None:
        on_watch_loaded()
    watch_modules = snapshot_app_modules()
    restore_app_modules(control_plane_modules)
    wrapped = wrap_inprocess_watch_app(watch_app, watch_modules)
    return wrapped, control_plane_modules
