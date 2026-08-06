"""run_store.list_failed_runs_since — indexed query VAXON fleet self-heal detect relies on."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.persistence import run_store  # noqa: E402


def _run(run_id: str, *, phase: str, updated_at: str) -> dict:
    return {
        "run_id": run_id,
        "workspace_id": "workspace_axon_watch",
        "lane_id": "lane_a",
        "mode": "agent",
        "status": phase,
        "phase": phase,
        "summary": "s",
        "detail": "d",
        "started_at": updated_at,
        "updated_at": updated_at,
        "ended_at": updated_at,
        "can_stop": False,
        "can_resume": False,
        "can_approve": False,
        "can_review": False,
        "current_step": "",
        "history_ref": f"history_{run_id}",
        "employee_role": "watcher",
        "task_id": None,
    }


class ListFailedRunsSinceTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)

    def test_only_failed_phase_returned(self) -> None:
        run_store.save_run(_run("run_failed", phase="failed", updated_at="2026-01-01T00:00:00Z"))
        run_store.save_run(_run("run_completed", phase="completed", updated_at="2026-01-01T00:00:00Z"))
        results = run_store.list_failed_runs_since("2020-01-01T00:00:00Z")
        self.assertEqual(["run_failed"], [r["run_id"] for r in results])

    def test_only_runs_at_or_after_since_returned(self) -> None:
        run_store.save_run(_run("run_old", phase="failed", updated_at="2020-01-01T00:00:00Z"))
        run_store.save_run(_run("run_new", phase="failed", updated_at="2026-06-01T00:00:00Z"))
        results = run_store.list_failed_runs_since("2026-01-01T00:00:00Z")
        self.assertEqual(["run_new"], [r["run_id"] for r in results])

    def test_boundary_since_timestamp_is_inclusive(self) -> None:
        run_store.save_run(_run("run_boundary", phase="failed", updated_at="2026-01-01T00:00:00Z"))
        results = run_store.list_failed_runs_since("2026-01-01T00:00:00Z")
        self.assertEqual(["run_boundary"], [r["run_id"] for r in results])

    def test_ordered_ascending_by_updated_at(self) -> None:
        run_store.save_run(_run("run_b", phase="failed", updated_at="2026-01-02T00:00:00Z"))
        run_store.save_run(_run("run_a", phase="failed", updated_at="2026-01-01T00:00:00Z"))
        results = run_store.list_failed_runs_since("2020-01-01T00:00:00Z")
        self.assertEqual(["run_a", "run_b"], [r["run_id"] for r in results])


if __name__ == "__main__":
    unittest.main()
