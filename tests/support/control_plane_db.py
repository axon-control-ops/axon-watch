from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import patch


def isolate_control_plane_db(testcase, run_store) -> str:
    tempdir = tempfile.TemporaryDirectory()
    testcase.addCleanup(tempdir.cleanup)

    db_path = str(Path(tempdir.name) / "control-plane.sqlite3")
    env_patch = patch.dict(
        os.environ,
        {
            "AXON_WATCH_CONTROL_PLANE_DB": db_path,
            # Keep TestClient lifespan from starting continuous worker ticks.
            "AXON_WATCH_WORKER_SCHEDULER": "0",
        },
        clear=False,
    )
    env_patch.start()
    testcase.addCleanup(env_patch.stop)

    run_store.reset_store()
    testcase.addCleanup(run_store.reset_store)
    return db_path
