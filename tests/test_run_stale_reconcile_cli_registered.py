"""Stale reaper must not reap executing runs with a live CLI registry entry."""

from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.persistence import run_store  # noqa: E402
from app.runs.service import append_run_execution_receipt, create_run, get_run  # noqa: E402
from app.runs.stale_reconcile import reap_stale_employee_runs  # noqa: E402


def _age_run(run_id: str, *, seconds: int) -> None:
    stamp = (
        datetime.now(timezone.utc) - timedelta(seconds=seconds)
    ).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    stored = run_store.get_run(run_id)
    assert stored is not None
    stored["started_at"] = stamp
    stored["updated_at"] = stamp
    run_store.save_run(stored)
    run_store.backdate_last_transition(str(stored["history_ref"]), stamp)


class RunStaleReconcileCliRegisteredTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)

    def test_reap_skips_executing_run_while_cli_runtime_registered(self) -> None:
        record = create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Rowan: CI repair Axon-X Fast Gate",
            employee_role="watcher",
        )
        run_id = str(record["run_id"])
        _age_run(run_id, seconds=900)
        append_run_execution_receipt(
            run_id,
            receipt_type="worker_heartbeat",
            receipt_summary="Continuous worker dispatch still running",
            actor="workspace_scheduler",
        )

        with patch(
            "app.cli_runtime.process_registry.is_registered",
            return_value=True,
        ):
            reaped = reap_stale_employee_runs(stale_seconds=600)

        self.assertEqual(reaped, [])
        self.assertEqual("executing", get_run(run_id)["phase"])


if __name__ == "__main__":
    unittest.main()
