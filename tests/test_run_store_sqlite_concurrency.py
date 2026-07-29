from __future__ import annotations

import concurrent.futures
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.persistence import run_store_sqlite  # noqa: E402


class RunStoreSqliteConcurrencyTests(unittest.TestCase):
    def test_connections_use_wal_and_extended_busy_timeout(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            db_path = str(Path(tempdir) / "control-plane.sqlite3")
            with closing(run_store_sqlite.connect(db_path)) as connection:
                journal_mode = connection.execute("PRAGMA journal_mode").fetchone()[0]
                busy_timeout = connection.execute("PRAGMA busy_timeout").fetchone()[0]
                synchronous = connection.execute("PRAGMA synchronous").fetchone()[0]

        self.assertEqual("wal", str(journal_mode).lower())
        self.assertEqual(30_000, busy_timeout)
        self.assertEqual(1, synchronous)  # NORMAL

    def test_concurrent_writers_wait_instead_of_raising_locked(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            db_path = str(Path(tempdir) / "control-plane.sqlite3")

            def write(index: int) -> None:
                with closing(run_store_sqlite.connect(db_path)) as connection:
                    connection.execute(
                        """
                        INSERT INTO operator_presence_settings (
                            settings_key, settings_json, updated_at
                        ) VALUES (?, ?, ?)
                        """,
                        (f"concurrent-{index}", "{}", f"2026-07-29T20:00:{index:02d}Z"),
                    )
                    connection.commit()

            with concurrent.futures.ThreadPoolExecutor(max_workers=12) as executor:
                futures = [executor.submit(write, index) for index in range(24)]
                for future in futures:
                    future.result(timeout=10)

            with closing(run_store_sqlite.connect(db_path)) as connection:
                count = connection.execute(
                    "SELECT COUNT(*) FROM operator_presence_settings"
                ).fetchone()[0]
            self.assertEqual(24, count)


if __name__ == "__main__":
    unittest.main()
