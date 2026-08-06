"""VAXON fleet self-heal: sidecar event/signal store CRUD and status transitions."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.fleet_self_heal import store  # noqa: E402


class FleetRepairEventStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        store.reset_store_for_tests()
        self.addCleanup(store.reset_store_for_tests)

    def test_upsert_observation_creates_event_with_first_occurrence(self) -> None:
        event = store.upsert_observation(
            "fleetbug:sandbox_resolution:abc123",
            subsystem="sandbox_resolution",
            file_hint="app/workspace_agents/agent_sandbox.py",
            workspace_id="workspace_dashpro",
            role="backend",
            run_id="run_1",
        )
        self.assertEqual(1, event["occurrence_count"])
        self.assertEqual("observed", event["status"])
        self.assertEqual(["workspace_dashpro"], event["workspaces_json"])
        self.assertEqual(["backend"], event["roles_json"])
        self.assertEqual(["run_1"], event["sample_run_ids_json"])

    def test_repeated_observation_increments_count_and_accumulates_distinct_values(self) -> None:
        fingerprint = "fleetbug:sandbox_resolution:abc123"
        store.upsert_observation(
            fingerprint, subsystem="sandbox_resolution", file_hint="x",
            workspace_id="workspace_dashpro", role="backend", run_id="run_1",
        )
        event = store.upsert_observation(
            fingerprint, subsystem="sandbox_resolution", file_hint="x",
            workspace_id="workspace_kairo", role="watcher", run_id="run_2",
        )
        self.assertEqual(2, event["occurrence_count"])
        self.assertEqual(["workspace_dashpro", "workspace_kairo"], event["workspaces_json"])
        self.assertEqual(["backend", "watcher"], event["roles_json"])
        self.assertEqual(["run_1", "run_2"], event["sample_run_ids_json"])

    def test_sample_lists_cap_at_eight_most_recent(self) -> None:
        fingerprint = "fleetbug:x:1"
        for i in range(12):
            event = store.upsert_observation(
                fingerprint, subsystem="x", file_hint="",
                workspace_id="workspace_a", role="watcher", run_id=f"run_{i}",
            )
        self.assertEqual(12, event["occurrence_count"])
        self.assertEqual(8, len(event["sample_run_ids_json"]))
        self.assertEqual([f"run_{i}" for i in range(4, 12)], event["sample_run_ids_json"])

    def test_observed_at_uses_the_failing_runs_own_timestamp_not_wall_clock(self) -> None:
        # A backlog scanner processing an old failure "now" must not record
        # last_seen_at as "now" — that would make a stale cluster look fresh.
        fingerprint = "fleetbug:x:1"
        old_timestamp = "2020-01-01T00:00:00Z"
        event = store.upsert_observation(
            fingerprint, subsystem="x", file_hint="",
            workspace_id="workspace_a", role="watcher", run_id="run_1",
            observed_at=old_timestamp,
        )
        self.assertEqual(old_timestamp, event["first_seen_at"])
        self.assertEqual(old_timestamp, event["last_seen_at"])

    def test_observed_at_last_seen_only_advances_forward(self) -> None:
        fingerprint = "fleetbug:x:1"
        store.upsert_observation(
            fingerprint, subsystem="x", file_hint="",
            workspace_id="workspace_a", role="watcher", run_id="run_1",
            observed_at="2026-01-01T00:00:00Z",
        )
        event = store.upsert_observation(
            fingerprint, subsystem="x", file_hint="",
            workspace_id="workspace_a", role="watcher", run_id="run_2",
            observed_at="2025-01-01T00:00:00Z",  # out-of-order backfill
        )
        self.assertEqual(
            "2026-01-01T00:00:00Z", event["last_seen_at"],
            "last_seen_at must not regress on an out-of-order/backfilled observation",
        )

    def test_attach_task_sets_status_and_bumps_lifetime_dispatch_count(self) -> None:
        fingerprint = "fleetbug:x:1"
        store.upsert_observation(
            fingerprint, subsystem="x", file_hint="",
            workspace_id="workspace_a", role="watcher", run_id="run_1",
        )
        store.attach_task(fingerprint, "task_123", status="repairing")
        event = store.get_event(fingerprint)
        assert event is not None
        self.assertEqual("task_123", event["task_id"])
        self.assertEqual("repairing", event["status"])
        self.assertEqual(1, event["lifetime_dispatch_count"])

    def test_bump_attempts_increments_and_returns_new_value(self) -> None:
        fingerprint = "fleetbug:x:1"
        store.upsert_observation(
            fingerprint, subsystem="x", file_hint="",
            workspace_id="workspace_a", role="watcher", run_id="run_1",
        )
        self.assertEqual(1, store.bump_attempts(fingerprint))
        self.assertEqual(2, store.bump_attempts(fingerprint))

    def test_record_verified_fix_resets_attempts_and_sets_commit_ref(self) -> None:
        fingerprint = "fleetbug:x:1"
        store.upsert_observation(
            fingerprint, subsystem="x", file_hint="",
            workspace_id="workspace_a", role="watcher", run_id="run_1",
        )
        store.bump_attempts(fingerprint)
        store.bump_attempts(fingerprint)
        store.record_verified_fix(fingerprint, commit_ref="abc123def", verified_at="2026-08-06T00:00:00Z")
        event = store.get_event(fingerprint)
        assert event is not None
        self.assertEqual("verified_fixed", event["status"])
        self.assertEqual(0, event["attempts_used"])
        self.assertEqual("abc123def", event["resolution_commit_ref"])
        self.assertEqual("2026-08-06T00:00:00Z", event["resolution_verified_at"])

    def test_known_blocked_signal_for_matches_workspace_and_role(self) -> None:
        fingerprint = "fleetbug:x:1"
        store.upsert_observation(
            fingerprint, subsystem="x", file_hint="",
            workspace_id="workspace_dashpro", role="backend", run_id="run_1",
        )
        store.attach_task(fingerprint, "task_1", status="repairing")
        result = store.known_blocked_signal_for("workspace_dashpro", "backend")
        self.assertIsNotNone(result)
        assert result is not None
        self.assertIn(fingerprint, result)

    def test_known_blocked_signal_for_returns_none_when_no_match(self) -> None:
        self.assertIsNone(store.known_blocked_signal_for("workspace_dashpro", "backend"))


class FleetRepairSignalStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        store.reset_store_for_tests()
        self.addCleanup(store.reset_store_for_tests)

    def test_upsert_signal_then_list_open_signals(self) -> None:
        store.upsert_signal(
            signal_id="sig_1", fingerprint="fleetbug:x:1", workspace_id="workspace_axon_watch",
            title="Sandbox path bug", summary="repeated sandbox failures",
            severity="high", status="open",
        )
        open_signals = store.list_open_signals()
        self.assertEqual(1, len(open_signals))
        self.assertEqual("sig_1", open_signals[0]["signal_id"])

    def test_resolve_signal_removes_it_from_open_list(self) -> None:
        store.upsert_signal(
            signal_id="sig_1", fingerprint="fleetbug:x:1", workspace_id="workspace_axon_watch",
            title="t", summary="s", severity="high", status="open",
        )
        resolved = store.resolve_signal("sig_1", reason="verified_fixed")
        assert resolved is not None
        self.assertEqual("resolved", resolved["status"])
        self.assertEqual("verified_fixed", resolved["meta"]["resolved_reason"])
        self.assertEqual([], store.list_open_signals())

    def test_resolve_signal_returns_none_for_unknown_id(self) -> None:
        self.assertIsNone(store.resolve_signal("does_not_exist"))


if __name__ == "__main__":
    unittest.main()
