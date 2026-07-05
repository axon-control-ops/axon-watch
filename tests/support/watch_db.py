from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import patch


def isolate_watch_db(testcase) -> str:
    tempdir = tempfile.TemporaryDirectory()
    testcase.addCleanup(tempdir.cleanup)

    db_path = str(Path(tempdir.name) / "axon-watch.sqlite3")
    env_patch = patch.dict(
        os.environ,
        {"AXON_WATCH_WATCH_SERVICE_DB": db_path},
        clear=False,
    )
    env_patch.start()
    testcase.addCleanup(env_patch.stop)
    return db_path
