"""Terminal employee run retention pruning."""

from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta, timezone
from typing import Any, Callable
from unittest.mock import AsyncMock, patch

from tests.support.control_plane_app_loader import load_control_plane_app, prepare_control_plane_imports
from tests.support.control_plane_db import isolate_control_plane_db

run_store: Any
create_run: Callable[..., dict[str, Any]]
complete_run: Callable[..., dict[str, Any]]
fail_run: Callable[..., dict[str, Any]]
get_run: Callable[..., dict[str, Any]]
list_runs: Callable[[], list[dict[str, Any]]]
prune_terminal_employee_runs: Callable[..., list[str]]
drain_terminal_employee_runs: Callable[..., list[str]]


class RunEmployeeRetentionTests(unittest.TestCase):
    def setUp(self) -> None:
        self._saved_modules = prepare_control_plane_imports()
        self.addCleanup(self._restore_control_plane_modules)

        global run_store, create_run, complete_run, fail_run, get_run, list_runs
        global prune_terminal_employee_runs, drain_terminal_employee_runs

        from app.persistence import run_store as _run_store
        from app.runs.service import (
            complete_run as _complete_run,
            create_run as _create_run,
            drain_terminal_employee_runs as _drain_terminal_employee_runs,
            fail_run as _fail_run,
            get_run as _get_run,
            list_runs as _list_runs,
            prune_terminal_employee_runs as _prune_terminal_employee_runs,
        )

        run_store = _run_store
        create_run = _create_run
        complete_run = _complete_run
        fail_run = _fail_run
        get_run = _get_run
        list_runs = _list_runs
        prune_terminal_employee_runs = _prune_terminal_employee_runs
        drain_terminal_employee_runs = _drain_terminal_employee_runs

        isolate_control_plane_db(self, run_store)

    def _restore_control_plane_modules(self) -> None:
        for name in list(sys.modules):
            if name == "app" or name.startswith("app."):
                del sys.modules[name]
        sys.modules.update(self._saved_modules)

    def _seed_employee_run(
        self,
        *,
        workspace_id: str = "workspace_axon_watch",
        role: str = "backend",
        summary: str = "Control Plane: continuous worker shift",
        age_seconds: int = 0,
    ) -> str:
        record = create_run(
            workspace_id=workspace_id,
            mode="agent",
            summary=summary,
            employee_role=role,
        )
        run_id = str(record["run_id"])
        if age_seconds:
            stamp = (
                datetime.now(timezone.utc) - timedelta(seconds=age_seconds)
            ).replace(microsecond=0).isoformat().replace("+00:00", "Z")
            stored = get_run(run_id)
            assert stored is not None
            stored["started_at"] = stamp
            stored["updated_at"] = stamp
            run_store.save_run(stored)
        complete_run(run_id)
        if age_seconds:
            stamp = (
                datetime.now(timezone.utc) - timedelta(seconds=age_seconds)
            ).replace(microsecond=0).isoformat().replace("+00:00", "Z")
            stored = get_run(run_id)
            assert stored is not None
            stored["ended_at"] = stamp
            stored["updated_at"] = stamp
            run_store.save_run(stored)
        return run_id

    def test_prune_keeps_recent_terminal_employee_runs_per_role(self) -> None:
        kept: list[str] = []
        for index in range(10):
            kept.append(
                self._seed_employee_run(
                    summary=f"Control Plane shift {index}",
                    age_seconds=1000 - index,
                )
            )

        pruned = prune_terminal_employee_runs(keep_per_role=3)

        self.assertEqual(7, len(pruned))
        remaining = [
            str(record["run_id"])
            for record in list_runs()
            if str(record.get("employee_role") or "").strip() == "backend"
        ]
        self.assertEqual(3, len(remaining))
        self.assertEqual(set(remaining), set(kept[-3:]))

    def test_prune_leaves_untagged_and_active_employee_runs_alone(self) -> None:
        terminal = self._seed_employee_run()
        active = create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Control Plane: live shift",
            employee_role="backend",
        )
        untagged = create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Operator git status",
        )

        pruned = prune_terminal_employee_runs(keep_per_role=0, max_deletes=10)

        self.assertEqual([terminal], pruned)
        self.assertIsNotNone(get_run(str(active["run_id"])))
        self.assertIsNotNone(get_run(str(untagged["run_id"])))

    def test_prune_respects_max_deletes_budget(self) -> None:
        for index in range(6):
            self._seed_employee_run(summary=f"Control Plane shift {index}")

        pruned = prune_terminal_employee_runs(keep_per_role=1, max_deletes=2)

        self.assertEqual(2, len(pruned))

    def test_prune_honors_retention_env(self) -> None:
        for index in range(4):
            self._seed_employee_run(summary=f"Control Plane shift {index}")

        with patch.dict(
            "os.environ",
            {"AXON_WATCH_EMPLOYEE_RUN_RETENTION_PER_ROLE": "2"},
            clear=False,
        ):
            pruned = prune_terminal_employee_runs()

        self.assertEqual(2, len(pruned))

    def test_prune_is_scoped_by_workspace_and_role(self) -> None:
        backend_axon = self._seed_employee_run(role="backend", workspace_id="workspace_axon_watch")
        backend_dashpro = self._seed_employee_run(role="backend", workspace_id="workspace_dashpro")
        frontend_axon = self._seed_employee_run(role="frontend", workspace_id="workspace_axon_watch")

        pruned = prune_terminal_employee_runs(keep_per_role=0, max_deletes=10)

        self.assertEqual(
            {backend_axon, backend_dashpro, frontend_axon},
            set(pruned),
        )

    def test_prune_includes_failed_and_cancelled_employee_runs(self) -> None:
        failed = create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Control Plane: failed shift",
            employee_role="backend",
        )
        failed_id = str(failed["run_id"])
        fail_run(failed_id)

        cancelled = create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Control Plane: cancelled shift",
            employee_role="backend",
        )
        cancelled_id = str(cancelled["run_id"])
        run_store.save_run({**get_run(cancelled_id), "phase": "cancelled", "status": "stopped"})

        pruned = prune_terminal_employee_runs(keep_per_role=0, max_deletes=10)

        self.assertEqual({failed_id, cancelled_id}, set(pruned))

    def test_drain_clears_backlog_beyond_one_tick_budget(self) -> None:
        for index in range(12):
            self._seed_employee_run(
                summary=f"Control Plane shift {index}",
                age_seconds=2000 - index,
            )

        drained = drain_terminal_employee_runs(
            keep_per_role=2,
            max_deletes_per_round=3,
            max_rounds=10,
        )

        self.assertEqual(10, len(drained))
        remaining = [
            record
            for record in list_runs()
            if str(record.get("employee_role") or "").strip() == "backend"
        ]
        self.assertEqual(2, len(remaining))

    def test_bootstrap_prunes_terminal_employee_runs_on_startup(self) -> None:
        from fastapi.testclient import TestClient

        for index in range(4):
            self._seed_employee_run(summary=f"Control Plane shift {index}")

        with patch.dict(
            "os.environ",
            {
                "AXON_WATCH_WORKER_SCHEDULER": "1",
                "AXON_WATCH_EMPLOYEE_RUN_RETENTION_PER_ROLE": "2",
            },
            clear=False,
        ), patch(
            "app.bootstrap.start_continuous_worker_scheduler",
            new=AsyncMock(return_value=None),
        ), patch(
            "app.bootstrap.stop_continuous_worker_scheduler",
            new=AsyncMock(),
        ):
            with TestClient(load_control_plane_app()) as client:
                remaining = [
                    record
                    for record in list_runs()
                    if str(record.get("employee_role") or "").strip() == "backend"
                ]
                self.assertEqual(2, len(remaining))

    def test_scheduler_tick_prunes_terminal_employee_runs(self) -> None:
        from app.workspace_agents.scheduler import run_continuous_worker_tick

        for index in range(5):
            self._seed_employee_run(summary=f"Control Plane shift {index}")

        with patch(
            "app.workspace_agents.scheduler.load_workspace_agent_configs",
            return_value=({}, {}, {}, []),
        ), patch.dict(
            "os.environ",
            {
                "AXON_WATCH_WORKER_SCHEDULER": "1",
                "AXON_WATCH_EMPLOYEE_RUN_RETENTION_PER_ROLE": "2",
            },
            clear=False,
        ):
            run_continuous_worker_tick()

        remaining = [
            record
            for record in list_runs()
            if str(record.get("employee_role") or "").strip() == "backend"
        ]
        self.assertEqual(2, len(remaining))

    def test_prune_api_returns_pruned_run_ids(self) -> None:
        from fastapi.testclient import TestClient

        for index in range(12):
            self._seed_employee_run(
                summary=f"Control Plane shift {index}",
                age_seconds=2000 - index,
            )

        with patch.dict(
            "os.environ",
            {"AXON_WATCH_EMPLOYEE_RUN_RETENTION_PER_ROLE": "2"},
            clear=False,
        ):
            client = TestClient(load_control_plane_app())
            try:
                response = client.post("/api/runs/prune-employee-history")
            finally:
                client.close()

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual(10, payload["count"])
        self.assertEqual(2, payload["keep_per_role"])
        self.assertEqual(10, len(payload["pruned_run_ids"]))
        remaining = [
            record
            for record in list_runs()
            if str(record.get("employee_role") or "").strip() == "backend"
        ]
        self.assertEqual(2, len(remaining))


if __name__ == "__main__":
    unittest.main()
