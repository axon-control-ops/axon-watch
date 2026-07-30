"""Stale role-tagged worker run reconciliation."""

from __future__ import annotations

import os
import sys
import threading
import time
import unittest
from datetime import datetime, timedelta, timezone
from typing import Any, Callable
from unittest.mock import AsyncMock, patch

from tests.support.control_plane_app_loader import prepare_control_plane_imports
from tests.support.control_plane_db import isolate_control_plane_db

run_store: Any
create_run: Callable[..., dict[str, Any]]
get_run: Callable[..., dict[str, Any]]
reap_stale_employee_runs: Callable[..., list[str]]
stop_run: Callable[..., dict[str, Any]]
touch_run_activity: Callable[..., dict[str, Any] | None]
append_run_execution_receipt: Callable[..., None]
_active_role_run_exists: Callable[..., bool]
run_continuous_worker_tick: Callable[..., list[dict[str, Any]]]


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


def _leased_worker_run(
    *,
    workspace_id: str,
    employee_role: str,
    summary: str,
) -> dict[str, Any]:
    from app.persistence import task_store

    opened = task_store.create_task(
        workspace_id=workspace_id,
        goal=summary,
        owner_role=employee_role,
    )
    leased = task_store.lease_task(
        opened["task_id"],
        lease_holder=f"employee-{workspace_id}-{employee_role}",
    )
    return create_run(
        workspace_id=workspace_id,
        mode="agent",
        summary=summary,
        employee_role=employee_role,
        task_id=leased["task_id"],
        require_leased_task=True,
    )


class RunStaleReconcileTests(unittest.TestCase):
    def setUp(self) -> None:
        self._saved_modules = prepare_control_plane_imports()
        self.addCleanup(self._restore_control_plane_modules)

        global run_store, create_run, get_run, reap_stale_employee_runs, stop_run
        global touch_run_activity, append_run_execution_receipt
        global _active_role_run_exists, run_continuous_worker_tick

        from app.persistence import run_store as _run_store
        from app.runs.service import (
            append_run_execution_receipt as _append_run_execution_receipt,
            create_run as _create_run,
            get_run as _get_run,
            reap_stale_employee_runs as _reap_stale_employee_runs,
            stop_run as _stop_run,
            touch_run_activity as _touch_run_activity,
        )
        from app.workspace_agents.scheduler import (
            _active_role_run_exists as _active_role_run_exists_fn,
            run_continuous_worker_tick as _run_continuous_worker_tick,
        )

        run_store = _run_store
        create_run = _create_run
        get_run = _get_run
        reap_stale_employee_runs = _reap_stale_employee_runs
        stop_run = _stop_run
        touch_run_activity = _touch_run_activity
        append_run_execution_receipt = _append_run_execution_receipt
        _active_role_run_exists = _active_role_run_exists_fn
        run_continuous_worker_tick = _run_continuous_worker_tick

        isolate_control_plane_db(self, run_store)

    def _restore_control_plane_modules(self) -> None:
        for name in list(sys.modules):
            if name == "app" or name.startswith("app."):
                del sys.modules[name]
        sys.modules.update(self._saved_modules)

    def test_reap_fails_old_employee_executing_runs(self) -> None:
        record = create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Control Plane: continuous worker shift",
            employee_role="backend",
        )
        run_id = str(record["run_id"])
        _age_run(run_id, seconds=900)

        reaped = reap_stale_employee_runs(stale_seconds=600)

        self.assertEqual(reaped, [run_id])
        self.assertEqual("failed", get_run(run_id)["phase"])
        history = run_store.list_history(get_run(run_id)["history_ref"])
        summaries = [str(item.get("receipt", {}).get("summary") or "") for item in history]
        self.assertTrue(any("stale timeout" in summary for summary in summaries))

    def test_reap_uses_last_receipt_so_active_long_runs_survive(self) -> None:
        record = create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Control Plane: long active shift",
            employee_role="backend",
        )
        run_id = str(record["run_id"])
        _age_run(run_id, seconds=1800)
        append_run_execution_receipt(
            run_id,
            receipt_type="worker_progress",
            receipt_summary="Continuous worker still executing",
            actor="workspace_scheduler",
        )

        reaped = reap_stale_employee_runs(stale_seconds=600)

        self.assertEqual(reaped, [])
        self.assertEqual("executing", get_run(run_id)["phase"])

    def test_worker_heartbeat_alone_does_not_block_stale_reaper(self) -> None:
        record = create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Control Plane: heartbeat shift",
            employee_role="backend",
        )
        run_id = str(record["run_id"])
        _age_run(run_id, seconds=900)
        append_run_execution_receipt(
            run_id,
            receipt_type="worker_heartbeat",
            receipt_summary="Continuous worker dispatch still running",
            actor="workspace_scheduler",
        )

        reaped = reap_stale_employee_runs(stale_seconds=600)

        self.assertEqual(reaped, [run_id])
        self.assertEqual("failed", get_run(run_id)["phase"])

    def test_stale_reaper_fails_hung_dispatch_with_only_heartbeats(self) -> None:
        record = create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Control Plane: hung dispatch shift",
            employee_role="backend",
        )
        run_id = str(record["run_id"])
        append_run_execution_receipt(
            run_id,
            receipt_type="worker_dispatch_started",
            receipt_summary="Continuous worker dispatch started for role=backend",
            actor="workspace_scheduler",
        )
        _age_run(run_id, seconds=900)
        append_run_execution_receipt(
            run_id,
            receipt_type="worker_heartbeat",
            receipt_summary="Continuous worker dispatch still running",
            actor="workspace_scheduler",
        )

        reaped = reap_stale_employee_runs(stale_seconds=600)

        self.assertEqual(reaped, [run_id])
        self.assertEqual("failed", get_run(run_id)["phase"])

    def test_touch_run_activity_does_not_block_stale_reaper(self) -> None:
        record = create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Control Plane: heartbeat shift",
            employee_role="backend",
        )
        run_id = str(record["run_id"])
        _age_run(run_id, seconds=900)

        touched = touch_run_activity(run_id)
        assert touched is not None

        reaped = reap_stale_employee_runs(stale_seconds=600)

        self.assertEqual(reaped, [run_id])
        self.assertEqual("failed", get_run(run_id)["phase"])

    def test_reap_cancels_stale_employee_runs_in_early_busy_phases(self) -> None:
        workspace_id = "workspace_early_phase_gate"
        for phase in ("queued", "starting", "planning"):
            with self.subTest(phase=phase):
                record = create_run(
                    workspace_id=workspace_id,
                    mode="agent",
                    summary=f"Control Plane: stale {phase} worker shift",
                    employee_role="backend",
                )
                run_id = str(record["run_id"])
                stored = run_store.get_run(run_id)
                assert stored is not None
                stored["phase"] = phase
                stored["status"] = phase if phase != "queued" else "running"
                run_store.save_run(stored)
                _age_run(run_id, seconds=900)
                self.assertTrue(_active_role_run_exists(workspace_id, "backend"))

                reaped = reap_stale_employee_runs(stale_seconds=600)

                self.assertEqual([run_id], reaped)
                self.assertEqual("cancelled", get_run(run_id)["phase"])
                self.assertFalse(_active_role_run_exists(workspace_id, "backend"))

    def test_reap_cancels_abandoned_paused_employee_runs(self) -> None:
        record = create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Control Plane: paused worker shift",
            employee_role="backend",
        )
        run_id = str(record["run_id"])
        stop_run(run_id)
        self.assertEqual("paused", get_run(run_id)["phase"])
        _age_run(run_id, seconds=900)

        reaped = reap_stale_employee_runs(stale_seconds=600)

        self.assertEqual(reaped, [run_id])
        self.assertEqual("cancelled", get_run(run_id)["phase"])

    def test_reap_leaves_fresh_employee_runs_alone(self) -> None:
        record = create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Shell Craft: continuous worker shift",
            employee_role="frontend",
        )
        run_id = str(record["run_id"])

        reaped = reap_stale_employee_runs(stale_seconds=600)

        self.assertEqual(reaped, [])
        self.assertEqual("executing", get_run(run_id)["phase"])

    def test_lead_default_ttl_survives_specialist_stale_cutoff(self) -> None:
        from app.runs.stale_reconcile import (
            DEFAULT_LEAD_STALE_SECONDS,
            employee_run_stale_seconds_for_role,
        )

        self.assertGreaterEqual(
            employee_run_stale_seconds_for_role("lead"),
            DEFAULT_LEAD_STALE_SECONDS,
        )
        record = create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Dana: continuous worker shift",
            employee_role="lead",
        )
        run_id = str(record["run_id"])
        # Specialist TTL (720s) would reap this; Lead default is 1800s.
        _age_run(run_id, seconds=900)

        reaped = reap_stale_employee_runs()

        self.assertEqual(reaped, [])
        self.assertEqual("executing", get_run(run_id)["phase"])

    def test_reap_leaves_untagged_interactive_runs_alone(self) -> None:
        record = create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Manual operator task",
        )
        run_id = str(record["run_id"])
        _age_run(run_id, seconds=3600)

        reaped = reap_stale_employee_runs(stale_seconds=600)

        self.assertEqual(reaped, [])
        self.assertEqual("executing", get_run(run_id)["phase"])

    def test_reap_honors_stale_seconds_env(self) -> None:
        record = create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Control Plane: env TTL shift",
            employee_role="backend",
        )
        run_id = str(record["run_id"])
        _age_run(run_id, seconds=500)

        with patch.dict(
            "os.environ",
            {"AXON_WATCH_WORKER_RUN_STALE_SECONDS": "400"},
            clear=False,
        ):
            reaped = reap_stale_employee_runs()

        self.assertEqual(reaped, [run_id])
        self.assertEqual("failed", get_run(run_id)["phase"])

    def test_reap_leaves_employee_awaiting_approval_alone(self) -> None:
        record = create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Control Plane: guarded worker shift",
            employee_role="backend",
            requires_approval=True,
        )
        run_id = str(record["run_id"])
        _age_run(run_id, seconds=3600)

        reaped = reap_stale_employee_runs(stale_seconds=600)

        self.assertEqual(reaped, [])
        self.assertEqual("awaiting_approval", get_run(run_id)["phase"])

    def test_paused_employee_run_does_not_block_role_gate(self) -> None:
        record = create_run(
            workspace_id="workspace_role_gate",
            mode="agent",
            summary="Control Plane: paused gate shift",
            employee_role="backend",
        )
        stop_run(str(record["run_id"]))
        self.assertEqual("paused", get_run(str(record["run_id"]))["phase"])
        self.assertFalse(_active_role_run_exists("workspace_role_gate", "backend"))

    def test_scheduler_tick_reaps_before_starting(self) -> None:
        stale = create_run(
            workspace_id="workspace_sched_stale",
            mode="agent",
            summary="Sched API: continuous worker shift",
            employee_role="backend",
        )
        run_id = str(stale["run_id"])
        _age_run(run_id, seconds=900)

        with patch(
            "app.workspace_agents.scheduler.load_workspace_agent_configs",
            return_value=({}, {}, {}, []),
        ), patch.dict(
            "os.environ",
            {"AXON_WATCH_WORKER_SCHEDULER": "1"},
            clear=False,
        ):
            started = run_continuous_worker_tick()

        self.assertEqual(started, [])
        self.assertEqual("failed", get_run(run_id)["phase"])

    def test_scheduler_tick_reaps_when_env_scheduler_disabled(self) -> None:
        stale = create_run(
            workspace_id="workspace_sched_env_off",
            mode="agent",
            summary="Sched API: continuous worker shift",
            employee_role="backend",
        )
        run_id = str(stale["run_id"])
        _age_run(run_id, seconds=900)

        with patch(
            "app.workspace_agents.scheduler.load_workspace_agent_configs",
            return_value=({}, {}, {}, []),
        ), patch.dict(
            "os.environ",
            {"AXON_WATCH_WORKER_SCHEDULER": "0"},
            clear=False,
        ):
            started = run_continuous_worker_tick()

        self.assertEqual(started, [])
        self.assertEqual("failed", get_run(run_id)["phase"])

    def test_dispatch_heartbeat_receipts_refresh_stale_ttl(self) -> None:
        from app.workspace_agents.config_loader import EmployeeConfig
        from app.workspace_agents.worker_dispatch import dispatch_continuous_worker_run

        release = threading.Event()

        def blocked_lane_b(**_kwargs: object) -> dict[str, object]:
            release.wait(timeout=3.0)
            return {"dispatched": True, "runtime_label": "test", "content": "done"}

        created = _leased_worker_run(
            workspace_id="workspace_axon_watch",
            employee_role="backend",
            summary="Control Plane: live heartbeat shift",
        )
        run_id = str(created["run_id"])
        _age_run(run_id, seconds=900)

        with patch(
            "app.workspace_agents.worker_dispatch.generate_lane_b_result",
            side_effect=blocked_lane_b,
        ), patch(
            "app.workspace_agents.worker_dispatch._HEARTBEAT_SECONDS",
            0.05,
        ), patch(
            "app.workspace_agents.worker_dispatch.create_worker_isolation",
            return_value=__import__("pathlib").Path("/tmp/axon-si-test/checkout"),
        ), patch(
            "app.workspace_agents.worker_dispatch.worker_agent_workspace",
            return_value=__import__("pathlib").Path("/tmp/axon-si-test/checkout"),
        ), patch(
            "app.workspace_agents.worker_dispatch.cleanup_worker_isolation",
            return_value={"cleaned": True},
        ):
            worker = threading.Thread(
                target=dispatch_continuous_worker_run,
                kwargs={
                    "workspace_id": "workspace_axon_watch",
                    "employee": EmployeeConfig(
                        name="Control Plane",
                        role="backend",
                        owns="APIs and persistence",
                        schedule="continuous",
                    ),
                    "run_record": created,
                },
                daemon=True,
            )
            worker.start()
            # Heartbeat is on a 50ms interval under the patch; wait for the receipt
            # instead of a fixed sleep (CI load made 150ms flake).
            deadline = time.monotonic() + 2.0
            receipt_types: list[str] = []
            while time.monotonic() < deadline:
                history = run_store.list_history(get_run(run_id)["history_ref"])
                receipt_types = [
                    str(item.get("receipt", {}).get("type") or "") for item in history
                ]
                if "worker_heartbeat" in receipt_types:
                    break
                time.sleep(0.05)
            reaped = reap_stale_employee_runs(stale_seconds=600)
            release.set()
            worker.join(timeout=5.0)

        self.assertEqual(reaped, [])
        self.assertIn("worker_heartbeat", receipt_types)

    def test_stream_progress_keeps_long_active_dispatch_alive(self) -> None:
        from app.workspace_agents.config_loader import EmployeeConfig
        from app.workspace_agents.worker_dispatch import dispatch_continuous_worker_run

        release = threading.Event()
        progress_sent = threading.Event()

        def streaming_lane_b(**kwargs: object) -> dict[str, object]:
            on_chunk = kwargs.get("on_chunk")
            if callable(on_chunk):
                on_chunk("partial reply", "partial reply")
                progress_sent.set()
            release.wait(timeout=3.0)
            return {"dispatched": True, "runtime_label": "test", "content": "done"}

        created = _leased_worker_run(
            workspace_id="workspace_axon_watch",
            employee_role="backend",
            summary="Control Plane: streaming progress shift",
        )
        run_id = str(created["run_id"])
        _age_run(run_id, seconds=900)

        with patch(
            "app.workspace_agents.worker_dispatch.generate_lane_b_result",
            side_effect=streaming_lane_b,
        ), patch(
            "app.workspace_agents.worker_dispatch.create_worker_isolation",
            return_value=__import__("pathlib").Path("/tmp/axon-si-test/checkout"),
        ), patch(
            "app.workspace_agents.worker_dispatch.worker_agent_workspace",
            return_value=__import__("pathlib").Path("/tmp/axon-si-test/checkout"),
        ), patch(
            "app.workspace_agents.worker_dispatch.cleanup_worker_isolation",
            return_value={"cleaned": True},
        ):
            worker = threading.Thread(
                target=dispatch_continuous_worker_run,
                kwargs={
                    "workspace_id": "workspace_axon_watch",
                    "employee": EmployeeConfig(
                        name="Control Plane",
                        role="backend",
                        owns="APIs and persistence",
                        schedule="continuous",
                    ),
                    "run_record": created,
                },
                daemon=True,
            )
            worker.start()
            self.assertTrue(progress_sent.wait(timeout=1.0))
            reaped = reap_stale_employee_runs(stale_seconds=600)
            history = run_store.list_history(get_run(run_id)["history_ref"])
            receipt_types = [
                str(item.get("receipt", {}).get("type") or "") for item in history
            ]
            release.set()
            worker.join(timeout=5.0)

        self.assertEqual(reaped, [])
        self.assertIn("worker_progress", receipt_types)

    def test_bootstrap_reaps_stale_employee_runs_when_scheduler_disabled(self) -> None:
        from fastapi.testclient import TestClient

        from tests.support.control_plane_app_loader import load_control_plane_app

        record = create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Control Plane: startup stale shift",
            employee_role="backend",
        )
        run_id = str(record["run_id"])
        _age_run(run_id, seconds=900)

        app = load_control_plane_app()
        with patch.dict(
            os.environ,
            {"AXON_WATCH_WORKER_SCHEDULER": "0"},
            clear=False,
        ), patch(
            "app.bootstrap.reconcile_orphaned_runs_on_startup",
            return_value=[],
        ), patch(
            "app.bootstrap.start_continuous_worker_scheduler",
            new=AsyncMock(return_value=None),
        ), patch(
            "app.bootstrap.stop_continuous_worker_scheduler",
            new=AsyncMock(),
        ):
            with TestClient(app) as client:
                response = client.get("/api/health")
                self.assertEqual(200, response.status_code)

        self.assertEqual("failed", get_run(run_id)["phase"])

    def test_reconcile_stale_api_returns_reaped_run_ids(self) -> None:
        from fastapi.testclient import TestClient

        from tests.support.control_plane_app_loader import load_control_plane_app

        record = create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Control Plane: API stale shift",
            employee_role="backend",
        )
        run_id = str(record["run_id"])
        _age_run(run_id, seconds=900)

        client = TestClient(load_control_plane_app())
        try:
            response = client.post("/api/runs/reconcile-stale")
        finally:
            client.close()

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual([run_id], payload["reaped_run_ids"])
        self.assertEqual(1, payload["count"])
        self.assertEqual("failed", get_run(run_id)["phase"])


if __name__ == "__main__":
    unittest.main()
