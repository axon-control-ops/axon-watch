from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import patch


def isolate_control_plane_db(testcase, run_store) -> str:
    tempdir = tempfile.TemporaryDirectory()
    testcase.addCleanup(tempdir.cleanup)

    db_path = str(Path(tempdir.name) / "control-plane.sqlite3")
    repo_root = Path(__file__).resolve().parents[2]
    env_patch = patch.dict(
        os.environ,
        {
            "AXON_WATCH_CONTROL_PLANE_DB": db_path,
            "AXON_WATCH_WORKSPACE_BINDINGS_FILE": str(
                repo_root / "config" / "workspace-project-bindings.ci.json",
            ),
            # Keep TestClient lifespan from starting continuous worker ticks.
            "AXON_WATCH_WORKER_SCHEDULER": "0",
            # Run-phase transitions in isolated tests must never shell out to a
            # real notify-send: a live desktop session running this suite
            # would fire a real "Axon-X run failed" notification for every
            # fixture that transitions a run to failed/blocked/review_ready.
            "AXON_WATCH_NOTIFICATIONS_ENABLED": "0",
        },
        clear=False,
    )
    env_patch.start()
    testcase.addCleanup(env_patch.stop)

    run_store.reset_store()
    testcase.addCleanup(run_store.reset_store)
    return db_path


def isolate_workspace_bindings(testcase) -> str:
    tempdir = tempfile.TemporaryDirectory()
    testcase.addCleanup(tempdir.cleanup)

    bindings_file = Path(tempdir.name) / "workspace-project-bindings.json"
    bindings_file.write_text('{"bindings": {}}\n', encoding="utf-8")
    env_patch = patch.dict(
        os.environ,
        {"AXON_WATCH_WORKSPACE_BINDINGS_FILE": str(bindings_file)},
        clear=False,
    )
    env_patch.start()
    testcase.addCleanup(env_patch.stop)
    return str(bindings_file)
