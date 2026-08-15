from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.persistence import run_store_sqlite  # noqa: E402


class RunStoreSqliteConnectionTests(unittest.TestCase):
    def test_connection_context_commits_and_closes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = str(Path(temp_dir) / "control-plane.sqlite3")
            connection = run_store_sqlite.connect(db_path)
            with connection:
                connection.execute("CREATE TABLE connection_probe (value TEXT)")
                connection.execute("INSERT INTO connection_probe VALUES ('committed')")

            with self.assertRaises(sqlite3.ProgrammingError):
                connection.execute("SELECT 1")


if __name__ == "__main__":
    unittest.main()
