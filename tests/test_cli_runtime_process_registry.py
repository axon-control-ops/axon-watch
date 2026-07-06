from __future__ import annotations

import sys
import threading
import time
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.cli_runtime import process_registry  # noqa: E402
from app.cli_runtime.subprocess_runner import communicate_registered_process  # noqa: E402
from app.persistence import run_store  # noqa: E402
from tests.support.control_plane_db import isolate_control_plane_db  # noqa: E402


class CliRuntimeProcessRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        process_registry.clear_registry()

    def tearDown(self) -> None:
        process_registry.clear_registry()

    def test_terminate_unregisters_active_process(self) -> None:
        def _worker() -> None:
            communicate_registered_process(
                run_id="run_test_stop",
                command=[sys.executable, "-c", "import time; time.sleep(30)"],
                timeout_seconds=60,
            )

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()

        for _ in range(50):
            if process_registry.is_registered("run_test_stop"):
                break
            time.sleep(0.05)
        self.assertTrue(process_registry.is_registered("run_test_stop"))

        self.assertTrue(process_registry.terminate("run_test_stop"))
        thread.join(timeout=5)
        self.assertFalse(process_registry.is_registered("run_test_stop"))


class StopRunProcessRegistryIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)
        process_registry.clear_registry()

    def tearDown(self) -> None:
        process_registry.clear_registry()

    def test_stop_run_terminates_registered_cli_process(self) -> None:
        from app.runs.service import create_run, stop_run

        created = create_run(
            workspace_id="workspace_alpha",
            mode="agent",
            summary="CLI stop integration",
        )
        run_id = str(created["run_id"])

        def _worker() -> None:
            try:
                communicate_registered_process(
                    run_id=run_id,
                    command=[sys.executable, "-c", "import time; time.sleep(30)"],
                    timeout_seconds=60,
                )
            except RuntimeError:
                pass

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()

        for _ in range(50):
            if process_registry.is_registered(run_id):
                break
            time.sleep(0.05)
        self.assertTrue(process_registry.is_registered(run_id))

        stopped = stop_run(run_id)
        self.assertEqual("paused", stopped["phase"])
        thread.join(timeout=5)
        self.assertFalse(process_registry.is_registered(run_id))


if __name__ == "__main__":
    unittest.main()
