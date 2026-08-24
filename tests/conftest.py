import os
import sys
import builtins
from pathlib import Path

# Every run-phase transition fired by a test (fail_run/complete_run/mark_review_ready/...)
# goes through app.local_notifications.notify_run_transition, which shells out to a real
# notify-send if a live desktop DBUS session is present. tests/support/control_plane_db.py's
# isolate_control_plane_db() sets this per-testcase, but several test files roll their own
# ad hoc DB isolation and don't -- setdefault() here is a blanket safety net so running this
# suite on a real desktop never spams live "Axon-X run failed" notifications, while still
# letting a test that explicitly wants to exercise notify-send override this default.
os.environ.setdefault("AXON_WATCH_NOTIFICATIONS_ENABLED", "0")

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTROL_PLANE_ROOT = REPO_ROOT / "services" / "control-plane"
WATCH_SERVICE_ROOT = REPO_ROOT / "services" / "axon-watch"

_CONTROL_PLANE_MARKERS = (
    "services\" / \"control-plane",
    "services' / 'control-plane",
    "app.chat",
    "app.cli_runtime",
    "app.debug_prompt",
    "app.domain",
    "app.kairo",
    "app.persistence",
    "app.runs",
    "app.terminal",
    "app.workspace_agents",
    "app.workspace_catalog",
    "app.workspace_delivery",
)
_WATCH_SERVICE_MARKERS = (
    "services\" / \"axon-watch",
    "services' / 'axon-watch",
    "app.adapters",
    "app.commands",
    "app.email_account_resolve",
    "app.email_reply_suggest",
    "app.monitors",
    "app.signals",
    "app.skills_catalog",
)


def _clear_app_modules() -> None:
    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            del sys.modules[name]


def _prioritize_service_root(root: Path) -> None:
    root_path = str(root)
    for candidate in (str(CONTROL_PLANE_ROOT), str(WATCH_SERVICE_ROOT), root_path):
        while candidate in sys.path:
            sys.path.remove(candidate)
    sys.path.insert(0, root_path)


def _active_service_root() -> Path | None:
    roots = {str(CONTROL_PLANE_ROOT): CONTROL_PLANE_ROOT, str(WATCH_SERVICE_ROOT): WATCH_SERVICE_ROOT}
    for entry in sys.path:
        root = roots.get(entry)
        if root is not None:
            return root
    return None


def _service_root_for_source(source: str) -> Path | None:
    if "sys.path.insert(0, str(CONTROL_PLANE_ROOT))" in source:
        return CONTROL_PLANE_ROOT
    if "sys.path.insert(0, str(WATCH_ROOT))" in source or "sys.path.insert(0, str(WATCH_SERVICE_ROOT))" in source:
        return WATCH_SERVICE_ROOT
    if 'services" / "axon-watch' in source or "services' / 'axon-watch" in source:
        return WATCH_SERVICE_ROOT
    if 'services" / "control-plane' in source or "services' / 'control-plane" in source:
        return CONTROL_PLANE_ROOT
    watch_score = sum(marker in source for marker in _WATCH_SERVICE_MARKERS)
    control_score = sum(marker in source for marker in _CONTROL_PLANE_MARKERS)
    if not watch_score and not control_score:
        return None
    return WATCH_SERVICE_ROOT if watch_score > control_score else CONTROL_PLANE_ROOT


def _service_root_for_importing_test() -> Path | None:
    frame = sys._getframe(2)
    while frame is not None:
        filename = frame.f_code.co_filename
        path = Path(filename)
        if path.name.startswith("test_") and path.suffix == ".py":
            try:
                path.relative_to(REPO_ROOT / "tests")
                source = path.read_text(encoding="utf-8")
            except (OSError, ValueError):
                return None
            return _service_root_for_source(source)
        frame = frame.f_back
    return None


def _cached_app_root() -> Path | None:
    app_module = sys.modules.get("app")
    module_file = getattr(app_module, "__file__", None)
    if not module_file:
        return None
    try:
        path = Path(module_file).resolve()
    except OSError:
        return None
    for root in (CONTROL_PLANE_ROOT, WATCH_SERVICE_ROOT):
        try:
            path.relative_to(root)
            return root
        except ValueError:
            continue
    return None


_ORIGINAL_IMPORT = builtins.__import__
_IMPORT_GUARD_ACTIVE = False


def _service_app_import_guard(name, globals=None, locals=None, fromlist=(), level=0):  # type: ignore[no-untyped-def]
    global _IMPORT_GUARD_ACTIVE
    if level == 0 and (name == "app" or name.startswith("app.")):
        if _IMPORT_GUARD_ACTIVE:
            return _ORIGINAL_IMPORT(name, globals, locals, fromlist, level)
        _IMPORT_GUARD_ACTIVE = True
        try:
            desired = _service_root_for_importing_test() or _active_service_root()
            cached = _cached_app_root()
            if desired is not None:
                if cached is not None and cached != desired:
                    _clear_app_modules()
                _prioritize_service_root(desired)
            return _ORIGINAL_IMPORT(name, globals, locals, fromlist, level)
        finally:
            _IMPORT_GUARD_ACTIVE = False
    return _ORIGINAL_IMPORT(name, globals, locals, fromlist, level)


builtins.__import__ = _service_app_import_guard


def _prepare_service_imports_for_test(file_path: Path) -> None:
    if file_path.suffix != ".py" or not file_path.name.startswith("test_"):
        return
    try:
        source = file_path.read_text(encoding="utf-8")
    except OSError:
        return
    root = _service_root_for_source(source)
    if root is None:
        return
    _clear_app_modules()
    _prioritize_service_root(root)


def pytest_collect_file(file_path: Path, parent):  # type: ignore[no-untyped-def]
    """Keep the two service packages named ``app`` from poisoning each other."""
    _prepare_service_imports_for_test(file_path)
    return None


def pytest_pycollect_makemodule(module_path: Path, parent):  # type: ignore[no-untyped-def]
    """Reset the service ``app`` package immediately before module import.

    The suite mixes control-plane and watch-service tests. Individual test
    modules add the desired service root to ``sys.path``, but Python keeps the
    first imported top-level ``app`` package in ``sys.modules``. A full-suite
    collection can therefore bind later tests to the wrong service package.
    """
    _prepare_service_imports_for_test(module_path)
    return None
