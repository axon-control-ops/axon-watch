"""VAXON fleet self-heal: outcome marking, reconciliation, lifetime-cap escalation, inbox."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.fleet_self_heal import store  # noqa: E402
from app.fleet_self_heal.config import FleetSelfHealConfig  # noqa: E402
from app.fleet_self_heal.report import (  # noqa: E402
    fleet_repair_inbox_items,
    mark_repair_outcome,
    reconcile_linked_fleet_repair_outcomes,
)

_CONFIG = FleetSelfHealConfig(
    enabled=True, dispatch_enabled=True, target_workspace_id="workspace_axon_watch",
    owner_role="watcher", escalate_role="lead", attempt_budget_per_dispatch=3,
    max_dispatch_cycles=2, window_hours=6.0, repeat_occurrence_threshold=2,
    breadth_pair_threshold=2, min_scan_interval_seconds=300.0, push_policy="draft_pr",
)


class MarkRepairOutcomeTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        db_path = str(Path(self._tmpdir.name) / "cp.sqlite3")
        os.environ["AXON_WATCH_CONTROL_PLANE_DB"] = db_path
        self.addCleanup(lambda: os.environ.pop("AXON_WATCH_CONTROL_PLANE_DB", None))

        from app.persistence import run_store, task_store

        task_store.reset_store()
        run_store.reset_store()
        store.reset_store_for_tests()
        self.addCleanup(task_store.reset_store)
        self.addCleanup(run_store.reset_store)
        self.addCleanup(store.reset_store_for_tests)

        self.fingerprint = "fleetbug:sandbox_resolution:abc123"
        store.upsert_observation(
            self.fingerprint, subsystem="sandbox_resolution", file_hint="x",
            workspace_id="workspace_dashpro", role="backend", run_id="run_1",
        )

    def test_success_records_verified_fix_and_resolves_signal(self) -> None:
        signal = mark_repair_outcome(
            fingerprint=self.fingerprint, success=True, commit_ref="abc123def",
            detail="fixed", config=_CONFIG,
        )
        self.assertEqual("resolved", signal["status"])
        event = store.get_event(self.fingerprint)
        assert event is not None
        self.assertEqual("verified_fixed", event["status"])
        self.assertEqual("abc123def", event["resolution_commit_ref"])

    def test_success_completes_linked_task(self) -> None:
        from app.persistence import task_store

        opened = task_store.create_task(
            workspace_id="workspace_axon_watch", goal="VAXON fleet repair [...]", owner_role="watcher",
        )
        task_store.lease_task(str(opened["task_id"]), lease_holder="h")
        store.attach_task(self.fingerprint, str(opened["task_id"]), status="repairing")
        mark_repair_outcome(fingerprint=self.fingerprint, success=True, commit_ref="x", config=_CONFIG)
        task = task_store.get_task(str(opened["task_id"]))
        assert task is not None
        self.assertEqual("completed", task["status"])

    def test_failure_below_cap_keeps_signal_open_and_high(self) -> None:
        signal = mark_repair_outcome(
            fingerprint=self.fingerprint, success=False, detail="still failing", config=_CONFIG,
        )
        self.assertEqual("open", signal["status"])
        self.assertEqual("high", signal["severity"])
        event = store.get_event(self.fingerprint)
        assert event is not None
        self.assertNotEqual("blocked", event["status"])

    def test_failure_at_cap_blocks_and_escalates_to_lead(self) -> None:
        from app.persistence import task_store

        mark_repair_outcome(fingerprint=self.fingerprint, success=False, config=_CONFIG)  # attempt 1/2
        signal = mark_repair_outcome(fingerprint=self.fingerprint, success=False, config=_CONFIG)  # attempt 2/2 -> cap
        self.assertEqual("critical", signal["severity"])
        event = store.get_event(self.fingerprint)
        assert event is not None
        self.assertEqual("blocked", event["status"])
        lead_tasks = [
            t for t in task_store.list_tasks(workspace_id="workspace_axon_watch", status="open", limit=50)
            if t.get("owner_role") == "lead"
        ]
        self.assertEqual(1, len(lead_tasks))
        self.assertIn(self.fingerprint, str(lead_tasks[0]["goal"]))


class ReconciliationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        db_path = str(Path(self._tmpdir.name) / "cp.sqlite3")
        os.environ["AXON_WATCH_CONTROL_PLANE_DB"] = db_path
        self.addCleanup(lambda: os.environ.pop("AXON_WATCH_CONTROL_PLANE_DB", None))

        from app.persistence import run_store, task_store

        task_store.reset_store()
        run_store.reset_store()
        store.reset_store_for_tests()
        self.addCleanup(task_store.reset_store)
        self.addCleanup(run_store.reset_store)
        self.addCleanup(store.reset_store_for_tests)

    def test_reconcile_recovers_commit_ref_from_trailing_line_when_no_callback(self) -> None:
        from app.persistence import run_store, task_store

        fingerprint = "fleetbug:x:1"
        store.upsert_observation(
            fingerprint, subsystem="x", file_hint="", workspace_id="workspace_dashpro",
            role="backend", run_id="run_seed",
        )
        opened = task_store.create_task(workspace_id="workspace_axon_watch", goal="g", owner_role="watcher")
        task_store.lease_task(str(opened["task_id"]), lease_holder="h", run_id="run_worker")
        store.attach_task(fingerprint, str(opened["task_id"]), status="repairing")
        store.upsert_signal(
            signal_id=f"signal_fleet_repair_{fingerprint}", fingerprint=fingerprint,
            workspace_id="workspace_axon_watch", title="t", summary="s", severity="high", status="open",
        )

        run_store.save_run({
            "run_id": "run_worker", "workspace_id": "workspace_axon_watch", "lane_id": "l",
            "mode": "agent", "status": "completed", "phase": "completed", "summary": "s",
            "detail": "d", "started_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z",
            "ended_at": "2026-01-01T00:00:00Z", "can_stop": False, "can_resume": False,
            "can_approve": False, "can_review": False, "current_step": "",
            "history_ref": "history_run_worker", "employee_role": "watcher", "task_id": str(opened["task_id"]),
        })
        run_store.append_transition("history_run_worker", {
            "from_phase": "executing", "to_phase": "completed", "timestamp": "2026-01-01T00:00:00Z",
            "actor": "verifier", "current_step": "done",
            "receipt": {"type": "operator_complete", "summary": "Fixed it. Fix commit: abc999\nConfidence: 8/10"},
        })
        task_store.complete_task(str(opened["task_id"]), run_id="run_worker")

        reconciled = reconcile_linked_fleet_repair_outcomes(config=_CONFIG)
        self.assertEqual(1, len(reconciled))
        event = store.get_event(fingerprint)
        assert event is not None
        self.assertEqual("verified_fixed", event["status"])
        self.assertEqual("abc999", event["resolution_commit_ref"])


class InboxProjectionTests(unittest.TestCase):
    def setUp(self) -> None:
        store.reset_store_for_tests()
        self.addCleanup(store.reset_store_for_tests)

    def test_high_severity_signal_projects_as_interrupt(self) -> None:
        store.upsert_signal(
            signal_id="sig_1", fingerprint="fleetbug:x:1", workspace_id="workspace_axon_watch",
            title="t", summary="s", severity="critical", status="open",
        )
        items = fleet_repair_inbox_items(config=_CONFIG)
        self.assertEqual(1, len(items))
        self.assertEqual("fleet_self_heal", items[0]["source"])
        self.assertTrue(items[0]["watch_rule"]["interrupts"])


class RouteHandlerTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        db_path = str(Path(self._tmpdir.name) / "cp.sqlite3")
        os.environ["AXON_WATCH_CONTROL_PLANE_DB"] = db_path
        self.addCleanup(lambda: os.environ.pop("AXON_WATCH_CONTROL_PLANE_DB", None))

        from app.persistence import run_store, task_store

        task_store.reset_store()
        run_store.reset_store()
        store.reset_store_for_tests()
        self.addCleanup(task_store.reset_store)
        self.addCleanup(run_store.reset_store)
        self.addCleanup(store.reset_store_for_tests)

    def test_report_outcome_handler_requires_fingerprint(self) -> None:
        from fastapi import HTTPException

        from app.routes.fleet_self_heal import fleet_self_heal_report_outcome

        with self.assertRaises(HTTPException) as ctx:
            fleet_self_heal_report_outcome({"success": True})
        self.assertEqual(400, ctx.exception.status_code)

    def test_report_outcome_handler_marks_success(self) -> None:
        from app.routes.fleet_self_heal import fleet_self_heal_report_outcome

        fingerprint = "fleetbug:x:1"
        store.upsert_observation(
            fingerprint, subsystem="x", file_hint="", workspace_id="workspace_dashpro",
            role="backend", run_id="run_1",
        )
        response = fleet_self_heal_report_outcome(
            {"fingerprint": fingerprint, "success": True, "commit_ref": "abc", "detail": "fixed"}
        )
        self.assertTrue(response["ok"])
        self.assertEqual("resolved", response["status"])
        self.assertIn("fixed", response["spoken"])

    def test_route_registered_and_not_auth_exempt(self) -> None:
        from app.auth.middleware import _is_exempt

        self.assertFalse(_is_exempt("/api/fleet-self-heal/report-outcome"))


class InboxMergeTests(unittest.TestCase):
    def setUp(self) -> None:
        store.reset_store_for_tests()
        self.addCleanup(store.reset_store_for_tests)

    def test_build_inbox_response_merges_fleet_repair_items(self) -> None:
        from app.inbox_projection import build_inbox_response

        store.upsert_signal(
            signal_id="sig_merge_1", fingerprint="fleetbug:x:1", workspace_id="workspace_axon_watch",
            title="VAXON fleet bug: sandbox_resolution", summary="s", severity="high", status="open",
        )
        projected = build_inbox_response(
            inbox_fetcher=lambda: {"items": [], "count": 0, "updated_at": ""},
            allow_empty_unavailable=False,
        )
        titles = [str(item.get("title")) for item in projected["items"]]  # type: ignore[index]
        self.assertTrue(any("sandbox_resolution" in title for title in titles))


if __name__ == "__main__":
    unittest.main()
