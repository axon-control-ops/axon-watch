"""VAXON fleet self-heal: dispatch-stage goal/acceptance text, supersede, targeting, parking."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.fleet_self_heal import store  # noqa: E402
from app.fleet_self_heal.config import FleetSelfHealConfig  # noqa: E402
from app.fleet_self_heal.dispatch import (  # noqa: E402
    build_acceptance,
    build_repair_goal,
    create_and_lease_repair_task,
    dispatch_dispatchable_fingerprints,
    repair_goal_match_key,
    supersede_prior_repair_tasks,
)

_CONFIG = FleetSelfHealConfig(
    enabled=True, dispatch_enabled=True, target_workspace_id="workspace_axon_watch",
    owner_role="watcher", escalate_role="lead", attempt_budget_per_dispatch=3,
    max_dispatch_cycles=3, window_hours=6.0, repeat_occurrence_threshold=2,
    breadth_pair_threshold=2, min_scan_interval_seconds=300.0, push_policy="draft_pr",
)

_DRY_RUN_CONFIG = FleetSelfHealConfig(
    enabled=True, dispatch_enabled=False, target_workspace_id="workspace_axon_watch",
    owner_role="watcher", escalate_role="lead", attempt_budget_per_dispatch=3,
    max_dispatch_cycles=3, window_hours=6.0, repeat_occurrence_threshold=2,
    breadth_pair_threshold=2, min_scan_interval_seconds=300.0, push_policy="draft_pr",
)


def _sample_event(**overrides) -> dict:
    base = {
        "fingerprint": "fleetbug:sandbox_resolution:abc123",
        "subsystem": "sandbox_resolution",
        "file_hint": "app/workspace_agents/agent_sandbox.py",
        "status": "observed",
        "occurrence_count": 2,
        "workspaces_json": ["workspace_dashpro"],
        "roles_json": ["backend"],
        "sample_run_ids_json": ["run_1", "run_2"],
        "resolution_commit_ref": None,
        "resolution_verified_at": None,
    }
    base.update(overrides)
    return base


class GoalAndAcceptanceTextTests(unittest.TestCase):
    def test_goal_embeds_evidence(self) -> None:
        event = _sample_event()
        goal = build_repair_goal(event, fingerprint=event["fingerprint"])
        self.assertIn(event["fingerprint"], goal)
        self.assertIn("run_1", goal)
        self.assertIn("run_2", goal)
        self.assertIn("workspace_dashpro:backend", goal)
        self.assertIn("app/workspace_agents/agent_sandbox.py", goal)
        self.assertIn("occurrences=2", goal)
        self.assertTrue(goal.startswith(repair_goal_match_key(event["fingerprint"])))

    def test_regressed_goal_flags_prior_fix_and_warns_against_resubmitting(self) -> None:
        event = _sample_event(
            status="regressed", resolution_commit_ref="abc123def", resolution_verified_at="2026-01-01T00:00:00Z",
        )
        goal = build_repair_goal(event, fingerprint=event["fingerprint"])
        self.assertIn("REGRESSION", goal)
        self.assertIn("abc123def", goal)
        self.assertIn("do not just resubmit the same diff", goal)

    def test_acceptance_requires_regression_test_and_fast_gate_and_report_callback(self) -> None:
        event = _sample_event()
        acceptance = build_acceptance(event, config=_CONFIG)
        self.assertIn("regression test", acceptance)
        self.assertIn("Fast Gate", acceptance)
        self.assertIn("/api/fleet-self-heal/report-outcome", acceptance)
        self.assertIn(event["fingerprint"], acceptance)
        self.assertIn("Confidence: N/10", acceptance)
        self.assertIn("Never force-push or merge protected branches", acceptance)


class DispatchIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        db_path = str(Path(self._tmpdir.name) / "cp.sqlite3")
        os.environ["AXON_WATCH_CONTROL_PLANE_DB"] = db_path
        self.addCleanup(lambda: os.environ.pop("AXON_WATCH_CONTROL_PLANE_DB", None))

        from app.persistence import run_store, task_store
        from app.workspace_agents import lead_plan_store

        task_store.reset_store()
        run_store.reset_store()
        lead_plan_store.reset_store()
        store.reset_store_for_tests()
        self.addCleanup(task_store.reset_store)
        self.addCleanup(run_store.reset_store)
        self.addCleanup(lead_plan_store.reset_store)
        self.addCleanup(store.reset_store_for_tests)

    def test_dispatch_always_targets_axon_watch_even_when_failure_observed_elsewhere(self) -> None:
        from app.persistence import task_store

        event = _sample_event()  # workspaces_json = ["workspace_dashpro"]
        leased = create_and_lease_repair_task(config=_CONFIG, event=event, fingerprint=event["fingerprint"])
        task = task_store.get_task(str(leased["task_id"]))
        assert task is not None
        self.assertEqual("workspace_axon_watch", task["workspace_id"])
        self.assertNotEqual("workspace_dashpro", task["workspace_id"])
        self.assertEqual("watcher", task["owner_role"])
        self.assertEqual("leased", task["status"])

    def test_subsystem_role_override_routes_to_backend(self) -> None:
        from app.persistence import task_store

        config = FleetSelfHealConfig(
            enabled=True, dispatch_enabled=True, target_workspace_id="workspace_axon_watch",
            owner_role="watcher", escalate_role="lead", attempt_budget_per_dispatch=3,
            max_dispatch_cycles=3, window_hours=6.0, repeat_occurrence_threshold=2,
            breadth_pair_threshold=2, min_scan_interval_seconds=300.0, push_policy="draft_pr",
            subsystem_role_overrides={"persistence.run_store": "backend"},
        )
        event = _sample_event(subsystem="persistence.run_store")
        leased = create_and_lease_repair_task(config=config, event=event, fingerprint=event["fingerprint"])
        task = task_store.get_task(str(leased["task_id"]))
        assert task is not None
        self.assertEqual("backend", task["owner_role"])

    def test_supersede_cancels_prior_open_task_for_same_fingerprint(self) -> None:
        from app.persistence import task_store

        event = _sample_event()
        first = create_and_lease_repair_task(config=_CONFIG, event=event, fingerprint=event["fingerprint"])
        # Force it back to a supersede-able state (open), then supersede.
        task_store.fail_task(
            str(first["task_id"]), terminal_outcome="simulated", reopen_if_budget_remaining=True
        )
        cancelled = supersede_prior_repair_tasks(
            workspace_id="workspace_axon_watch", fingerprint=event["fingerprint"]
        )
        self.assertEqual(1, len(cancelled))
        task = task_store.get_task(str(first["task_id"]))
        assert task is not None
        self.assertEqual("cancelled", task["status"])

    def test_attach_task_records_fingerprint_status_in_store(self) -> None:
        event = _sample_event()
        store.upsert_observation(
            event["fingerprint"], subsystem=event["subsystem"], file_hint=event["file_hint"],
            workspace_id="workspace_dashpro", role="backend", run_id="run_1",
        )
        create_and_lease_repair_task(config=_CONFIG, event=event, fingerprint=event["fingerprint"])
        stored = store.get_event(event["fingerprint"])
        assert stored is not None
        self.assertEqual("repairing", stored["status"])
        self.assertIsNotNone(stored["task_id"])

    def test_parks_under_active_ship_plan_with_receipt_and_broadcast(self) -> None:
        from app.persistence import task_store
        from app.workspace_agents import lead_plan_store

        plan = lead_plan_store.persist_plan(
            workspace_id="workspace_axon_watch",
            plan={"goal": "Ship OTA canary for DashPro", "mode": "fan_out"},
            plan_key_to_task_id={},
        )
        event = _sample_event()
        store.upsert_observation(
            event["fingerprint"], subsystem=event["subsystem"], file_hint=event["file_hint"],
            workspace_id="workspace_dashpro", role="backend", run_id="run_1",
        )

        with mock.patch("app.live_events.broadcast_material_change") as broadcast_mock:
            parked = create_and_lease_repair_task(config=_CONFIG, event=event, fingerprint=event["fingerprint"])

        self.assertEqual(plan["plan_id"], parked.get("parked_under_plan"))
        task = task_store.get_task(str(parked.get("task_id") or ""))
        assert task is not None
        self.assertEqual("lead", task["owner_role"])
        self.assertIn("Lead: advance", str(task["goal"]))
        self.assertIn(event["fingerprint"], str(task["goal"]))

        receipts = lead_plan_store.list_receipts(str(plan["plan_id"]))
        matching = [r for r in receipts if r.get("kind") == "fleet_repair_finding_parked"]
        self.assertEqual(1, len(matching))
        self.assertEqual(event["fingerprint"], matching[0]["payload"]["fingerprint"])
        self.assertFalse(matching[0]["payload"]["reused_sticky_lead_task"])
        broadcast_mock.assert_called_once()

        stored_event = store.get_event(event["fingerprint"])
        assert stored_event is not None
        self.assertEqual("repairing", stored_event["status"])

    def test_dry_run_config_never_dispatches(self) -> None:
        from app.persistence import task_store

        event = _sample_event()
        store.upsert_observation(
            event["fingerprint"], subsystem=event["subsystem"], file_hint=event["file_hint"],
            workspace_id="workspace_dashpro", role="backend", run_id="run_1",
        )
        dispatched = dispatch_dispatchable_fingerprints(
            config=_DRY_RUN_CONFIG, fingerprints=[event["fingerprint"]]
        )
        self.assertEqual([], dispatched)
        self.assertEqual([], task_store.list_tasks(workspace_id="workspace_axon_watch", status="open", limit=10))


if __name__ == "__main__":
    unittest.main()
