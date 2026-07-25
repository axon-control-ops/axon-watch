"""Abandoned operator review_ready reconciliation."""

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
get_run: Callable[..., dict[str, Any]]
mark_review_ready: Callable[..., dict[str, Any]]
reap_abandoned_review_ready_runs: Callable[..., list[str]]


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


class RunReviewReadyReconcileTests(unittest.TestCase):
    def setUp(self) -> None:
        self._saved_modules = prepare_control_plane_imports()
        self.addCleanup(self._restore_control_plane_modules)

        global run_store, create_run, get_run, mark_review_ready
        global reap_abandoned_review_ready_runs

        from app.persistence import run_store as _run_store
        from app.runs.service import (
            create_run as _create_run,
            get_run as _get_run,
            mark_review_ready as _mark_review_ready,
            reap_abandoned_review_ready_runs as _reap_abandoned_review_ready_runs,
        )

        run_store = _run_store
        create_run = _create_run
        get_run = _get_run
        mark_review_ready = _mark_review_ready
        reap_abandoned_review_ready_runs = _reap_abandoned_review_ready_runs

        isolate_control_plane_db(self, run_store)

    def _restore_control_plane_modules(self) -> None:
        for name in list(sys.modules):
            if name == "app" or name.startswith("app."):
                del sys.modules[name]
        sys.modules.update(self._saved_modules)

    def _seed_review_ready(
        self,
        *,
        summary: str = "Run npm test",
        age_seconds: int = 0,
        employee_role: str | None = None,
        workspace_id: str = "workspace_axon_watch",
    ) -> str:
        record = create_run(
            workspace_id=workspace_id,
            mode="agent",
            summary=summary,
            employee_role=employee_role,
        )
        run_id = str(record["run_id"])
        mark_review_ready(run_id)
        if age_seconds:
            _age_run(run_id, seconds=age_seconds)
        return run_id

    def test_reap_completes_old_untagged_review_ready_runs(self) -> None:
        run_id = self._seed_review_ready(age_seconds=20_000)

        completed = reap_abandoned_review_ready_runs(stale_seconds=14_400)

        self.assertEqual([run_id], completed)
        self.assertEqual("completed", get_run(run_id)["phase"])
        history = run_store.list_history(get_run(run_id)["history_ref"])
        summaries = [str(item.get("receipt", {}).get("summary") or "") for item in history]
        self.assertTrue(any("Abandoned review_ready" in summary for summary in summaries))
        types = [str(item.get("receipt", {}).get("type") or "") for item in history]
        self.assertIn("review_ready_abandon", types)

    def test_reap_leaves_fresh_review_ready_alone(self) -> None:
        run_id = self._seed_review_ready(age_seconds=60)

        completed = reap_abandoned_review_ready_runs(stale_seconds=14_400)

        self.assertEqual([], completed)
        self.assertEqual("review_ready", get_run(run_id)["phase"])

    def test_reap_leaves_role_tagged_review_ready_alone(self) -> None:
        run_id = self._seed_review_ready(
            summary="Control Plane: continuous worker shift",
            age_seconds=20_000,
            employee_role="backend",
        )

        completed = reap_abandoned_review_ready_runs(stale_seconds=14_400)

        self.assertEqual([], completed)
        self.assertEqual("review_ready", get_run(run_id)["phase"])

    def test_reap_leaves_approval_waits_alone(self) -> None:
        record = create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Deploy guarded change",
            requires_approval=True,
        )
        run_id = str(record["run_id"])
        _age_run(run_id, seconds=20_000)

        completed = reap_abandoned_review_ready_runs(stale_seconds=14_400)

        self.assertEqual([], completed)
        self.assertEqual("awaiting_approval", get_run(run_id)["phase"])

    def test_reap_honors_stale_seconds_env(self) -> None:
        run_id = self._seed_review_ready(age_seconds=500)

        with patch.dict(
            "os.environ",
            {"AXON_WATCH_REVIEW_READY_STALE_SECONDS": "300"},
            clear=False,
        ):
            completed = reap_abandoned_review_ready_runs()

        self.assertEqual([run_id], completed)
        self.assertEqual("completed", get_run(run_id)["phase"])

    def test_scheduler_tick_completes_abandoned_review_ready(self) -> None:
        from app.workspace_agents.scheduler import run_continuous_worker_tick

        run_id = self._seed_review_ready(age_seconds=20_000)

        with patch(
            "app.workspace_agents.scheduler.load_workspace_agent_configs",
            return_value=({}, {}, {}, []),
        ), patch.dict(
            "os.environ",
            {
                "AXON_WATCH_WORKER_SCHEDULER": "1",
                "AXON_WATCH_REVIEW_READY_STALE_SECONDS": "3600",
            },
            clear=False,
        ):
            run_continuous_worker_tick()

        self.assertEqual("completed", get_run(run_id)["phase"])

    def test_bootstrap_completes_abandoned_review_ready_on_startup(self) -> None:
        from fastapi.testclient import TestClient

        run_id = self._seed_review_ready(age_seconds=20_000)

        with patch.dict(
            "os.environ",
            {
                "AXON_WATCH_WORKER_SCHEDULER": "0",
                "AXON_WATCH_REVIEW_READY_STALE_SECONDS": "3600",
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
                self.assertEqual("completed", get_run(run_id)["phase"])
                response = client.get("/api/health")
                self.assertEqual(200, response.status_code)

    def test_reconcile_review_ready_api_returns_completed_run_ids(self) -> None:
        from fastapi.testclient import TestClient

        run_id = self._seed_review_ready(age_seconds=20_000)

        with patch.dict(
            "os.environ",
            {"AXON_WATCH_REVIEW_READY_STALE_SECONDS": "3600"},
            clear=False,
        ):
            client = TestClient(load_control_plane_app())
            try:
                response = client.post("/api/runs/reconcile-review-ready")
            finally:
                client.close()

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual(1, payload["count"])
        self.assertEqual([run_id], payload["completed_run_ids"])
        self.assertEqual(3600.0, payload["stale_seconds"])
        self.assertEqual("completed", get_run(run_id)["phase"])


if __name__ == "__main__":
    unittest.main()
