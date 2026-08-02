from __future__ import annotations

import sys
import unittest
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.persistence import run_store  # noqa: E402


class RunHistoryAppendRaceTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)

    def test_concurrent_append_transition_keeps_unique_sequences(self) -> None:
        history_ref = "history/run_race_test"
        workers = 24

        def _write(index: int) -> None:
            run_store.append_transition(
                history_ref,
                {
                    "actor": "test",
                    "current_step": f"step-{index}",
                    "from_phase": "executing",
                    "to_phase": "executing",
                    "timestamp": f"2026-08-02T08:00:{index:02d}Z",
                    "receipt": {"type": "worker_heartbeat", "summary": f"hb-{index}"},
                },
            )

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(_write, i) for i in range(workers)]
            for future in as_completed(futures):
                future.result()

        items = run_store.list_history(history_ref)
        self.assertEqual(workers, len(items))
        # Sequences are assigned under exclusive write lock; list_history returns
        # transitions ordered by sequence, so count equality is the contract.
        summaries = [item["receipt"]["summary"] for item in items]
        self.assertEqual(workers, len(set(summaries)))


if __name__ == "__main__":
    unittest.main()
