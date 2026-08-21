"""Every control-plane module must import cleanly on its own, in any order.

Regression guard for two real incidents in one session:

1. scheduler.py imported reap_stale_interactive_runs from app.runs.service,
   which only re-exports an explicit named list from stale_reconcile -- the
   new function was never added to that list. This crash-looped the live
   control-plane service on every boot (33+ restarts) because nothing in the
   test suite ever imported app.workspace_agents.scheduler or app.main.

2. capability_routing.py imported select_verification_commands from
   verification_execution.py at module load time, but verification_execution's
   own import chain circles back to capability_routing (through
   app.persistence). Importing capability_routing *first* in a fresh process
   crashed; importing verification_execution first happened to mask it, which
   is exactly why this kind of bug survives individual-module smoke tests and
   only shows up depending on unrelated import order elsewhere in the app.

A single test that imports app.main (already covered by
test_control_plane_data.py) only proves *one* import order works. This test
recursively imports every app.* submodule directly and independently, so an
order-dependent circular import cannot hide behind whatever order app.main
happens to trigger.
"""

from __future__ import annotations

import importlib
import pkgutil
import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))


class ControlPlaneImportGraphTests(unittest.TestCase):
    def test_every_app_submodule_imports_independently(self) -> None:
        errors: list[tuple[str, Exception]] = []
        checked = 0

        def walk(module_name: str) -> None:
            nonlocal checked
            try:
                module = importlib.import_module(module_name)
            except Exception as exc:  # noqa: BLE001 — collecting every failure, not just the first
                errors.append((module_name, exc))
                return
            checked += 1
            if hasattr(module, "__path__"):
                for info in pkgutil.iter_modules(module.__path__, prefix=f"{module_name}."):
                    walk(info.name)

        walk("app")
        self.assertGreater(checked, 100, "sanity check: the app package looks unexpectedly small")
        if errors:
            detail = "\n".join(f"  {name}: {type(exc).__name__}: {exc}" for name, exc in errors)
            self.fail(f"{len(errors)} module(s) failed to import cleanly:\n{detail}")


class ModuleImportedFirstInAFreshProcessTests(unittest.TestCase):
    """The single-process walk above has a real blind spot: once any earlier
    module has pulled in a dependency, every later import of it in that same
    process looks fine even if the two modules have a genuine circular
    import -- which is exactly how both incidents above survived a
    same-process recursive walk (proven: reverting either fix and re-running
    that walk still passes, because pkgutil's alphabetical order happens to
    import something that masks it before reaching the broken module).

    Each module here is imported as the *sole* first import in a clean
    subprocess -- no accumulated import state from anything else -- which is
    what actually reproduced both crashes.
    """

    # Modules with a demonstrated history of this fragility, or that sit on
    # the live service's own boot path (app.main) or scheduler tick
    # (app.workspace_agents.scheduler) where a crash here is a live outage,
    # not a test failure. Add to this list whenever a circular-import bug is
    # found the same way these two were.
    _MODULES = (
        "app.main",
        "app.workspace_agents.scheduler",
        "app.workspace_agents.capability_routing",
        "app.runs.service",
    )

    def test_module_imports_cleanly_as_the_first_import_in_the_process(self) -> None:
        import subprocess
        import sys

        for module_name in self._MODULES:
            with self.subTest(module=module_name):
                result = subprocess.run(
                    [sys.executable, "-c", f"import {module_name}"],
                    cwd=str(CONTROL_PLANE_ROOT),
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                self.assertEqual(
                    result.returncode,
                    0,
                    f"importing {module_name} as the first import failed:\n{result.stderr[-2000:]}",
                )


if __name__ == "__main__":
    unittest.main()
