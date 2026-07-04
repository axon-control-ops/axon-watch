from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.verify.common import compact_json_size_bytes, load_config

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES_DIR = REPO_ROOT / "packages" / "shared-types" / "fixtures"

RUN_MODES = {"ask", "agent", "plan", "auto", "watch"}
RUN_PHASES = {
    "queued",
    "starting",
    "planning",
    "awaiting_input",
    "awaiting_approval",
    "executing",
    "waiting_external",
    "paused",
    "review_ready",
    "completed",
    "failed",
    "cancelled",
}
RUN_STATUSES = {"running", "waiting", "blocked", "review", "done", "error", "stopped"}
SIGNAL_EVENT_TYPES = {
    "signal_opened",
    "signal_updated",
    "signal_escalated",
    "signal_deescalated",
    "signal_resolved",
    "signal_reopened",
    "delivery_attempted",
    "delivery_succeeded",
    "delivery_failed",
    "operator_acknowledged",
    "operator_dispatched",
    "operator_ignored",
}
SIGNAL_SEVERITIES = {"info", "warning", "high", "critical"}
SIGNAL_STATUSES = {"open", "watching", "acknowledged", "suppressed", "resolved", "failed_delivery"}
SIGNAL_SOURCES = {
    "runtime",
    "watch",
    "ci",
    "git",
    "connector",
    "email",
    "workspace",
    "browser",
    "terminal",
    "approval",
    "deployment",
    "manual",
}
SIGNAL_ACTION_TYPES = {
    "open_dashboard",
    "open_workspace",
    "open_approvals",
    "review_changes",
    "retry",
    "investigate",
    "dispatch",
    "resolve",
    "none",
}
DELIVERY_STATES = {"pending", "attempted", "delivered", "failed", "suppressed", "not_required"}
BRIEFING_ACTION_KINDS = {"approve_run", "resume_run", "review_signal", "inspect_runtime"}


def _load_fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


class SharedContractFixtureTests(unittest.TestCase):
    def test_run_record_fixture_matches_canonical_entity_fields(self) -> None:
        payload = _load_fixture("run-record.example.json")

        self.assertEqual(
            {
                "run_id",
                "workspace_id",
                "lane_id",
                "mode",
                "status",
                "phase",
                "summary",
                "detail",
                "started_at",
                "updated_at",
                "ended_at",
                "can_stop",
                "can_resume",
                "can_approve",
                "can_review",
                "current_step",
                "history_ref",
            },
            set(payload),
        )
        self.assertIn(payload["mode"], RUN_MODES)
        self.assertIn(payload["phase"], RUN_PHASES)
        self.assertIn(payload["status"], RUN_STATUSES)

    def test_runtime_summary_fixture_matches_boot_contract(self) -> None:
        payload = _load_fixture("runtime-summary.example.json")

        self.assertEqual(
            {
                "generated_at",
                "control_plane",
                "watch",
                "runtime_identity",
                "active_runs",
                "approvals",
                "signals",
                "capabilities",
                "degraded",
            },
            set(payload),
        )

        active_run = payload["active_runs"][0]
        self.assertEqual(
            {
                "run_id",
                "workspace_id",
                "mode",
                "status",
                "phase",
                "title",
                "detail",
                "lane_id",
                "updated_at",
            },
            set(active_run),
        )
        self.assertIn(active_run["mode"], RUN_MODES)
        self.assertIn(active_run["phase"], RUN_PHASES)
        self.assertIn(active_run["status"], RUN_STATUSES)

        top_item = payload["signals"]["top_items"][0]
        self.assertEqual(
            {
                "signal_id",
                "workspace_id",
                "title",
                "summary",
                "severity",
                "status",
                "source",
                "updated_at",
                "action_type",
            },
            set(top_item),
        )
        self.assertIn(top_item["severity"], SIGNAL_SEVERITIES)
        self.assertIn(top_item["status"], SIGNAL_STATUSES)
        self.assertIn(top_item["source"], SIGNAL_SOURCES)
        self.assertIn(top_item["action_type"], SIGNAL_ACTION_TYPES)

    def test_signal_event_fixture_matches_canonical_event_envelope(self) -> None:
        payload = _load_fixture("signal-event.example.json")

        self.assertEqual(
            {
                "event_id",
                "signal_id",
                "event_type",
                "source",
                "workspace_id",
                "project_id",
                "severity",
                "status",
                "title",
                "body",
                "summary",
                "created_at",
                "updated_at",
                "occurred_at",
                "dedupe_key",
                "action_type",
                "action_payload",
                "correlation_ref",
                "delivery_state",
                "meta",
            },
            set(payload),
        )
        self.assertIn(payload["event_type"], SIGNAL_EVENT_TYPES)
        self.assertIn(payload["severity"], SIGNAL_SEVERITIES)
        self.assertIn(payload["status"], SIGNAL_STATUSES)
        self.assertIn(payload["source"], SIGNAL_SOURCES)
        self.assertIn(payload["action_type"], SIGNAL_ACTION_TYPES)
        self.assertIn(payload["delivery_state"], DELIVERY_STATES)

    def test_minimal_identity_fixtures_exist_for_shell_families(self) -> None:
        approval = _load_fixture("approval-record.example.json")
        workspace = _load_fixture("workspace-record.example.json")
        thread = _load_fixture("thread-message.example.json")
        inbox_item = _load_fixture("inbox-item.example.json")

        self.assertEqual({"approval_id", "run_id", "workspace_id"}, set(approval))
        self.assertEqual({"workspace_id"}, set(workspace))
        self.assertEqual({"message_id", "thread_id", "run_id", "workspace_id"}, set(thread))
        self.assertEqual(
            {
                "signal_id",
                "workspace_id",
                "title",
                "summary",
                "severity",
                "status",
                "source",
                "updated_at",
                "action_type",
            },
            set(inbox_item),
        )

    def test_signal_identity_severity_and_status_stay_consistent_across_projections(self) -> None:
        runtime_summary = _load_fixture("runtime-summary.example.json")
        watch_summary = _load_fixture("watch-summary.example.json")
        signal_event = _load_fixture("signal-event.example.json")
        inbox_item = _load_fixture("inbox-item.example.json")

        runtime_top_item = runtime_summary["signals"]["top_items"][0]
        watch_inbox_item = watch_summary["inbox"]["items"][0]

        expected = (
            signal_event["signal_id"],
            signal_event["severity"],
            signal_event["status"],
        )

        self.assertEqual(expected, (runtime_top_item["signal_id"], runtime_top_item["severity"], runtime_top_item["status"]))
        self.assertEqual(expected, (watch_inbox_item["signal_id"], watch_inbox_item["severity"], watch_inbox_item["status"]))
        self.assertEqual(expected, (inbox_item["signal_id"], inbox_item["severity"], inbox_item["status"]))

    def test_operator_briefing_fixture_matches_projection_contract(self) -> None:
        payload = _load_fixture("operator-briefing.example.json")

        self.assertEqual(
            {
                "generated_at",
                "top_signals",
                "pending_approvals",
                "active_runs",
                "next_safe_actions",
                "degraded",
                "connectivity",
            },
            set(payload),
        )
        self.assertEqual({"count", "items"}, set(payload["pending_approvals"]))
        self.assertEqual({"active", "reasons"}, set(payload["degraded"]))
        self.assertEqual({"control_plane_ready", "watch_connected"}, set(payload["connectivity"]))

        action = payload["next_safe_actions"][0]
        self.assertEqual(
            {
                "action_id",
                "kind",
                "title",
                "detail",
                "workspace_id",
                "run_id",
                "signal_id",
            },
            set(action),
        )
        self.assertIn(action["kind"], BRIEFING_ACTION_KINDS)

    def test_runtime_and_watch_fixtures_fit_configured_size_budgets(self) -> None:
        config = load_config()["dto_sizes"]

        runtime_budget = int(config["runtime_summary"]["threshold_bytes"])
        watch_budget = int(config["watch_summary"]["threshold_bytes"])
        runtime_payload = FIXTURES_DIR / "runtime-summary.example.json"
        watch_payload = FIXTURES_DIR / "watch-summary.example.json"

        self.assertLessEqual(compact_json_size_bytes(runtime_payload), runtime_budget)
        self.assertLessEqual(compact_json_size_bytes(watch_payload), watch_budget)


if __name__ == "__main__":
    unittest.main()
