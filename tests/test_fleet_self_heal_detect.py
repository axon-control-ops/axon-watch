"""VAXON fleet self-heal: detect-stage windowed scan, thresholds, regression."""

from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.fleet_self_heal import store  # noqa: E402
from app.fleet_self_heal.config import FleetSelfHealConfig  # noqa: E402
from app.fleet_self_heal.detect import scan_fleet_failures  # noqa: E402

_LIST_FAILED = "app.fleet_self_heal.detect.run_store.list_failed_runs_since"
_LIST_HISTORY = "app.fleet_self_heal.detect.run_store.list_history"

_CONFIG = FleetSelfHealConfig(
    enabled=True, dispatch_enabled=False, target_workspace_id="workspace_axon_watch",
    owner_role="watcher", escalate_role="lead", attempt_budget_per_dispatch=3,
    max_dispatch_cycles=3, window_hours=6.0, repeat_occurrence_threshold=2,
    breadth_pair_threshold=2, min_scan_interval_seconds=300.0, push_policy="draft_pr",
)


def _run(run_id: str, *, workspace_id: str, role: str, updated_at: datetime) -> dict:
    return {
        "run_id": run_id,
        "workspace_id": workspace_id,
        "employee_role": role,
        "updated_at": updated_at.isoformat().replace("+00:00", "Z"),
        "history_ref": f"history_{run_id}",
        "phase": "failed",
    }


def _history_with_summary(summary: str) -> list[dict]:
    return [{"receipt": {"type": "run_failed", "summary": summary}}]


class DetectScanTests(unittest.TestCase):
    def setUp(self) -> None:
        store.reset_store_for_tests()
        self.addCleanup(store.reset_store_for_tests)
        self.state_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.state_dir.cleanup)
        self.state_path = Path(self.state_dir.name) / "scan-state.json"

    def test_gate_handled_failures_are_never_observed(self) -> None:
        now = datetime.now(timezone.utc)
        run = _run("run_1", workspace_id="workspace_dashpro", role="backend", updated_at=now)
        with patch(_LIST_FAILED, return_value=[run]), patch(
            _LIST_HISTORY, return_value=_history_with_summary("Out of usage — increase limits in Cursor")
        ):
            result = scan_fleet_failures(config=_CONFIG, now=now, state_path=self.state_path)
        self.assertEqual(0, result.fleet_infra_observations)
        self.assertEqual([], result.dispatchable_fingerprints)

    def test_single_isolated_occurrence_is_recorded_but_not_dispatched(self) -> None:
        now = datetime.now(timezone.utc)
        run = _run("run_1", workspace_id="workspace_dashpro", role="backend", updated_at=now)
        with patch(_LIST_FAILED, return_value=[run]), patch(
            _LIST_HISTORY, return_value=_history_with_summary("maximum recursion depth exceeded")
        ):
            result = scan_fleet_failures(config=_CONFIG, now=now, state_path=self.state_path)
        self.assertEqual(1, result.fleet_infra_observations)
        self.assertEqual([], result.dispatchable_fingerprints, "single occurrence is noise, not signal")

    def test_repeat_threshold_dispatches_same_workspace_role_twice(self) -> None:
        now = datetime.now(timezone.utc)
        runs = [
            _run("run_1", workspace_id="workspace_dashpro", role="backend", updated_at=now - timedelta(minutes=10)),
            _run("run_2", workspace_id="workspace_dashpro", role="backend", updated_at=now),
        ]
        with patch(_LIST_FAILED, return_value=runs), patch(
            _LIST_HISTORY, return_value=_history_with_summary("maximum recursion depth exceeded")
        ):
            result = scan_fleet_failures(config=_CONFIG, now=now, state_path=self.state_path)
        self.assertEqual(2, result.fleet_infra_observations)
        self.assertEqual(1, len(result.dispatchable_fingerprints))

    def test_breadth_threshold_dispatches_across_two_workspace_role_pairs(self) -> None:
        now = datetime.now(timezone.utc)
        runs = [
            _run("run_1", workspace_id="workspace_dashpro", role="backend", updated_at=now - timedelta(minutes=10)),
            _run("run_2", workspace_id="workspace_kairo", role="watcher", updated_at=now),
        ]
        with patch(_LIST_FAILED, return_value=runs), patch(
            _LIST_HISTORY, return_value=_history_with_summary("maximum recursion depth exceeded")
        ):
            result = scan_fleet_failures(config=_CONFIG, now=now, state_path=self.state_path)
        self.assertEqual(1, len(result.dispatchable_fingerprints), "distinct pairs should cross breadth threshold")

    def test_high_water_mark_prevents_double_counting_same_run_across_ticks(self) -> None:
        now = datetime.now(timezone.utc)
        run = _run("run_1", workspace_id="workspace_dashpro", role="backend", updated_at=now)
        with patch(_LIST_FAILED, return_value=[run]), patch(
            _LIST_HISTORY, return_value=_history_with_summary("maximum recursion depth exceeded")
        ):
            first = scan_fleet_failures(
                config=_CONFIG, now=now, state_path=self.state_path,
                min_interval_seconds=0,
            )
            second = scan_fleet_failures(
                config=_CONFIG, now=now + timedelta(seconds=1), state_path=self.state_path,
                min_interval_seconds=0,
            )
        self.assertEqual(1, first.fleet_infra_observations)
        self.assertEqual(
            0, second.fleet_infra_observations,
            "the same run_id must not be re-observed once past the high-water mark",
        )

    def test_min_interval_throttle_skips_repeat_scans(self) -> None:
        now = datetime.now(timezone.utc)
        run = _run("run_1", workspace_id="workspace_dashpro", role="backend", updated_at=now)
        with patch(_LIST_FAILED, return_value=[run]), patch(
            _LIST_HISTORY, return_value=_history_with_summary("maximum recursion depth exceeded")
        ):
            first = scan_fleet_failures(
                config=_CONFIG, now=now, state_path=self.state_path, min_interval_seconds=300,
            )
            second = scan_fleet_failures(
                config=_CONFIG, now=now + timedelta(seconds=30), state_path=self.state_path,
                min_interval_seconds=300,
            )
        self.assertFalse(first.skipped_min_interval)
        self.assertTrue(second.skipped_min_interval)
        self.assertEqual(0, second.fleet_infra_observations)

    def test_regression_detected_when_verified_fixed_fingerprint_reoccurs(self) -> None:
        now = datetime.now(timezone.utc)
        run = _run("run_new", workspace_id="workspace_dashpro", role="backend", updated_at=now)
        with patch(_LIST_HISTORY, return_value=_history_with_summary("maximum recursion depth exceeded")):
            # Seed a fingerprint that was already fixed in the past.
            with patch(_LIST_FAILED, return_value=[]):
                pass
            from app.fleet_self_heal.classify import classify_failure_signature
            signature = classify_failure_signature(detail="maximum recursion depth exceeded")
            store.upsert_observation(
                signature.fingerprint, subsystem=signature.subsystem, file_hint=signature.file_hint,
                workspace_id="workspace_dashpro", role="backend", run_id="run_old",
            )
            store.record_verified_fix(
                signature.fingerprint, commit_ref="abc123",
                verified_at=(now - timedelta(days=1)).isoformat().replace("+00:00", "Z"),
            )

            with patch(_LIST_FAILED, return_value=[run]):
                result = scan_fleet_failures(config=_CONFIG, now=now, state_path=self.state_path)

        self.assertEqual(1, len(result.regressed_fingerprints))
        self.assertEqual([], result.dispatchable_fingerprints, "regression is reported separately, not double-counted")
        event = store.get_event(signature.fingerprint)
        assert event is not None
        self.assertEqual("regressed", event["status"])

    def test_stale_cluster_outside_recency_window_is_not_dispatched(self) -> None:
        now = datetime.now(timezone.utc)
        old_config = FleetSelfHealConfig(
            enabled=True, dispatch_enabled=False, target_workspace_id="workspace_axon_watch",
            owner_role="watcher", escalate_role="lead", attempt_budget_per_dispatch=3,
            max_dispatch_cycles=3, window_hours=0.01, repeat_occurrence_threshold=2,
            breadth_pair_threshold=2, min_scan_interval_seconds=0, push_policy="draft_pr",
        )
        runs = [
            _run("run_1", workspace_id="workspace_dashpro", role="backend", updated_at=now - timedelta(hours=2)),
            _run("run_2", workspace_id="workspace_dashpro", role="backend", updated_at=now - timedelta(hours=2)),
        ]
        with patch(_LIST_FAILED, return_value=runs), patch(
            _LIST_HISTORY, return_value=_history_with_summary("maximum recursion depth exceeded")
        ):
            result = scan_fleet_failures(config=old_config, now=now, state_path=self.state_path)
        self.assertEqual([], result.dispatchable_fingerprints)


if __name__ == "__main__":
    unittest.main()
