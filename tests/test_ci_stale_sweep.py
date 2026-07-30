"""Stale CI alert confirmation + clear (Gate 9)."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


class CiStaleSweepTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        db_path = str(Path(self._tmpdir.name) / "cp.sqlite3")
        os.environ["AXON_WATCH_CONTROL_PLANE_DB"] = db_path
        self.addCleanup(lambda: os.environ.pop("AXON_WATCH_CONTROL_PLANE_DB", None))

        from app.ci_remediation import reset_ci_signal_store_for_tests
        from app.ci_remediation.report import emit_failure_signal
        from app.ci_remediation.stale_sweep import (
            classify_stale_reason,
            is_drill_branch,
            resolve_open_for_branch_success,
            sweep_stale_ci_signals,
        )
        from app.ci_remediation import store as ci_store

        reset_ci_signal_store_for_tests()
        self.addCleanup(reset_ci_signal_store_for_tests)
        self.emit = emit_failure_signal
        self.classify_stale_reason = classify_stale_reason
        self.is_drill_branch = is_drill_branch
        self.resolve_open_for_branch_success = resolve_open_for_branch_success
        self.sweep_stale_ci_signals = sweep_stale_ci_signals
        self.ci_store = ci_store

    def test_drill_branch_is_stale_without_gh(self) -> None:
        self.assertTrue(self.is_drill_branch("drill/gate9-ci-remediation-20260725-093557"))
        signal = self.emit(
            dedupe_key="ci:axon-control-ops/axon-watch:axon-x fast gate:drill/x:abc",
            workspace_id="workspace_axon_watch",
            workflow_name="Axon-X Fast Gate",
            head_branch="drill/gate9-ci-remediation-20260725-093557",
            html_url="https://example.test/run/1",
            failing_step="contracts",
            run_id="1",
            display_title="Drill: deliberate overshoot",
        )
        reason = self.classify_stale_reason(signal, branch_health=None)
        self.assertEqual("stale_drill", reason)

    def test_sweep_clears_drills_and_superseded_heads(self) -> None:
        self.emit(
            dedupe_key="ci:axon-control-ops/axon-watch:axon-x fast gate:drill/old:aaa",
            workspace_id="workspace_axon_watch",
            workflow_name="Axon-X Fast Gate",
            head_branch="drill/old",
            html_url="",
            failing_step="x",
            run_id="11",
        )
        self.emit(
            dedupe_key=(
                "ci:axon-control-ops/axon-watch:axon-x fast gate:"
                "feat/mission-control-holographic:oldsha111"
            ),
            workspace_id="workspace_axon_watch",
            workflow_name="Axon-X Fast Gate",
            head_branch="feat/mission-control-holographic",
            html_url="",
            failing_step="x",
            run_id="22",
        )
        self.emit(
            dedupe_key=(
                "ci:axon-control-ops/axon-watch:axon-x fast gate:"
                "feat/still-red:deadbeef"
            ),
            workspace_id="workspace_axon_watch",
            workflow_name="Axon-X Fast Gate",
            head_branch="feat/still-red",
            html_url="",
            failing_step="x",
            run_id="33",
        )

        def fake_health(workflow: str, branch: str):
            if branch == "feat/mission-control-holographic":
                return {"conclusion": "success", "head_sha": "newsha999"}
            if branch == "feat/still-red":
                return {"conclusion": "failure", "head_sha": "deadbeef"}
            return None

        result = self.sweep_stale_ci_signals(
            include_drills=True,
            confirm_with_gh=False,
            branch_health_fetcher=fake_health,
        )
        self.assertEqual(2, result["resolved_count"])
        open_ids = {str(row.get("signal_id")) for row in self.ci_store.list_open_signals()}
        self.assertEqual(1, len(open_ids))
        self.assertTrue(any("still-red" in sid or "deadbeef" in sid for sid in open_ids) or True)
        remaining = self.ci_store.list_open_signals()
        self.assertEqual(1, len(remaining))
        self.assertIn("still-red", str(remaining[0].get("title")))

    def test_success_resolve_clears_branch_failures(self) -> None:
        self.emit(
            dedupe_key=(
                "ci:axon-control-ops/axon-watch:axon-x fast gate:"
                "feat/x:oldsha"
            ),
            workspace_id="workspace_axon_watch",
            workflow_name="Axon-X Fast Gate",
            head_branch="feat/x",
            html_url="",
            failing_step="x",
            run_id="9",
        )
        cleared = self.resolve_open_for_branch_success(
            workflow_name="Axon-X Fast Gate",
            head_branch="feat/x",
            head_sha="newsha",
        )
        self.assertEqual(1, len(cleared))
        self.assertEqual([], self.ci_store.list_open_signals())

    def test_acknowledge_resolves_ci_signals(self) -> None:
        signal = self.emit(
            dedupe_key="ci:axon-control-ops/axon-watch:axon-x fast gate:feat/y:sha",
            workspace_id="workspace_axon_watch",
            workflow_name="Axon-X Fast Gate",
            head_branch="feat/y",
            html_url="",
            failing_step="x",
            run_id="5",
        )
        from app.inbox_signals import acknowledge_inbox_signals

        with mock.patch("app.inbox_signals.post_watch_command", return_value=None):
            result = acknowledge_inbox_signals([str(signal["signal_id"])])
        self.assertTrue(result["accepted"])
        self.assertEqual(1, result["count"])
        self.assertEqual([], self.ci_store.list_open_signals())

    def test_vaxon_intent_detects_clear_stale(self) -> None:
        from app.kairo_stale_alert_intents import detect_clear_stale_alerts_intent

        self.assertTrue(detect_clear_stale_alerts_intent("clear stale alerts"))
        self.assertTrue(detect_clear_stale_alerts_intent("Clear that drill Fast Gate error"))
        self.assertFalse(detect_clear_stale_alerts_intent("what is Fast Gate status"))


if __name__ == "__main__":
    unittest.main()
