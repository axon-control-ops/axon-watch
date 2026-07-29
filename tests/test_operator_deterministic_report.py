"""Deterministic REPORT lane — roster + verified Lead handoffs."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.support.control_plane_app_loader import prepare_control_plane_imports
from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))


_MOCK_BRIEFING = {
    "scope": {"workspace_id": "workspace_dashpro", "display_name": "DashPro"},
    "notice": "",
    "advise": "I'd check Priya's Lead next before starting more UI",
    "pending_approvals": {"count": 0},
    "top_signals": [],
    "active_runs": [],
    "next_safe_actions": [],
    "awaiting_engagement_count": 0,
    "degraded": {"active": False},
    "connectivity": {"watch_connected": True},
    "cli_runtime": {"dispatch_ready": True, "blockers": []},
}

_MOCK_FLEET = {
    "items": [
        {"workspace_id": "ws_a", "tone": "nominal"},
        {"workspace_id": "ws_b", "tone": "nominal"},
    ]
}
_MOCK_GRAPH = {"nodes": [], "edges": []}

_BRIEFING_PATCH = "app.kairo.conversation_context_pack.build_operator_briefing"
_FLEET_PATCH = "app.kairo.conversation_context_pack.build_operator_fleet_health"
_GRAPH_PATCH = "app.kairo.conversation_context_pack.build_operator_brain_graph"


class OperatorDeterministicReportTests(unittest.TestCase):
    def setUp(self) -> None:
        self._saved = prepare_control_plane_imports()
        self.addCleanup(self._restore)
        from app.persistence import chat_store, run_store, task_store
        from app.workspace_agents import lead_adhoc_receipt_store, lead_plan_store

        isolate_control_plane_db(self, run_store)
        task_store.reset_store()
        lead_plan_store.reset_store()
        lead_adhoc_receipt_store.reset_store()
        chat_store.reset_store()

    def _restore(self) -> None:
        for name in list(sys.modules):
            if name == "app" or name.startswith("app."):
                del sys.modules[name]
        sys.modules.update(self._saved)

    def test_report_intent_detects_hotwords_and_expanded_prompt(self) -> None:
        from app.kairo.operator_deterministic_report import is_operator_report_request

        self.assertTrue(is_operator_report_request("REPORT"))
        self.assertTrue(is_operator_report_request("status"))
        self.assertTrue(is_operator_report_request("where do we stand"))
        self.assertTrue(
            is_operator_report_request(
                "REPORT — give me a JARVIS-style second-brain stand-up in plain English."
            )
        )
        self.assertFalse(is_operator_report_request("any approvals?"))
        self.assertFalse(is_operator_report_request("open DashPro workspace"))

    def test_compose_names_busy_and_completed_and_receipt_handoffs(self) -> None:
        from app.kairo.operator_deterministic_report import (
            compose_operator_report,
        )
        from app.workspace_agents.lead_vaxon_handoff import post_ad_hoc_lead_takeover_to_vaxon

        with patch("app.live_events.broadcast_material_change"):
            posted = post_ad_hoc_lead_takeover_to_vaxon(
                workspace_id="workspace_dashpro",
                run_id="run_priya_done",
                employee_role="frontend",
                employee_name="Priya",
                phase="completed",
                lead_next="decide notify campaign once storage is live",
                lead_summary="Built parent graduation survey card",
                blockers="Marco owns storage/payment migration",
            )
        self.assertEqual("posted", posted.get("status"))

        snapshot = {
            "workspace_id": "workspace_dashpro",
            "briefing": _MOCK_BRIEFING,
            "fleet": _MOCK_FLEET,
            "roster": {
                "workspace_id": "workspace_dashpro",
                "company_name": "DashPro",
                "employees": [],
                "busy": [
                    {
                        "employee_id": "emp_marco",
                        "name": "Marco",
                        "role": "backend",
                        "role_label": "Backend",
                        "status": "executing",
                        "active_run_id": "run_marco_1",
                    }
                ],
                "completed": [
                    {
                        "employee_id": "emp_priya",
                        "name": "Priya",
                        "role": "frontend",
                        "role_label": "Frontend",
                        "status": "idle",
                        "last_outcome": "completed",
                    }
                ],
                "failed": [],
            },
            "handoffs": [
                {
                    "receipt_id": posted.get("receipt_id"),
                    "headline": "Priya (frontend) completed — Built parent graduation survey card",
                    "lead_next": "decide notify campaign once storage is live",
                    "lead_summary": "Built parent graduation survey card",
                }
            ],
            "top_signals": [],
            "active_runs": [],
            "pending_approvals": 0,
            "awaiting_engagement_count": 0,
            "next_safe_actions": [],
            "fingerprint": "abc",
        }
        composed = compose_operator_report(snapshot)
        text = composed["text"]
        self.assertIn("Attention:", text)
        self.assertIn("Work in flight:", text)
        self.assertIn("Marco (Backend) is executing", text)
        self.assertIn("Priya (Frontend) just completed", text)
        self.assertIn("Lead rollups:", text)
        self.assertIn("graduation survey", text.lower())
        self.assertIn("Plan:", text)
        self.assertNotIn("Confidence:", text)
        self.assertIn("Fleet:", text)
        self.assertIn("Next move:", text)

        # Empty state stays calm.
        empty = compose_operator_report(
            {
                "workspace_id": "workspace_dashpro",
                "briefing": {**_MOCK_BRIEFING, "advise": ""},
                "fleet": _MOCK_FLEET,
                "roster": {
                    "busy": [],
                    "completed": [],
                    "failed": [],
                    "employees": [],
                },
                "handoffs": [],
                "top_signals": [],
                "active_runs": [],
                "pending_approvals": 0,
                "awaiting_engagement_count": 0,
                "next_safe_actions": [],
                "fingerprint": "empty",
            }
        )
        self.assertIn("nothing screaming", empty["text"].lower())
        self.assertIn("idle", empty["text"].lower())
        self.assertIn("standing by", empty["text"].lower())

    def test_lead_rollup_scrubs_cli_dump_into_operator_line(self) -> None:
        from app.kairo.operator_deterministic_report import compose_operator_report

        headline = (
            "Mira (lead) failed — Lane B (agent) cannot start because no CLI runtime is ready: "
            "Codex CLI (local) unavailable; Cursor auth probe timed out. Run cursor agent status "
            "manually.; Cursor Cloud Agent unavailable; Codex Cloud Task unavailable. "
            "Open Runtime or /vault , then retry."
        )
        briefing = {
            **_MOCK_BRIEFING,
            # Keep the dump so scrubbing is exercised — healed CLI would drop it.
            "cli_runtime": {"dispatch_ready": False, "blockers": ["Cursor auth probe timed out"]},
        }
        composed = compose_operator_report(
            {
                "workspace_id": "workspace_axon_watch",
                "briefing": briefing,
                "fleet": _MOCK_FLEET,
                "roster": {"busy": [], "completed": [], "failed": [], "employees": []},
                "handoffs": [
                    {
                        "lead_name": "Mira",
                        "headline": headline,
                        "lead_next": "",
                    }
                ],
                "top_signals": [],
                "active_runs": [],
                "pending_approvals": 0,
                "awaiting_engagement_count": 0,
                "next_safe_actions": [],
                "fingerprint": "cli-dump-rollup",
            }
        )

        line = composed["sections"]["lead_rollups"][0]
        self.assertIn("Mira:", line)
        self.assertIn("no CLI runtime is ready", line)
        self.assertNotIn("invocation", line.lower())
        self.assertLessEqual(len(line), 180)

    def test_lead_rollup_strips_terminal_shell_laundry(self) -> None:
        from app.kairo.operator_deterministic_report import compose_operator_report

        headline = (
            "Mira (lead) completed. terminal ls -la "
            "/home/edp/axon-nvme/repos/axon-watch/control-plane.sqlite3 "
            "find /home/edp -name '*.sqlite' 2>/dev/null | head -20"
        )
        composed = compose_operator_report(
            {
                "workspace_id": "workspace_axon_watch",
                "briefing": _MOCK_BRIEFING,
                "fleet": _MOCK_FLEET,
                "roster": {"busy": [], "completed": [], "failed": [], "employees": []},
                "handoffs": [
                    {
                        "lead_name": "Mira",
                        "headline": headline,
                        "lead_next": "",
                    }
                ],
                "top_signals": [],
                "active_runs": [],
                "pending_approvals": 0,
                "awaiting_engagement_count": 0,
                "next_safe_actions": [],
                "fingerprint": "shell-laundry-rollup",
            }
        )

        line = composed["sections"]["lead_rollups"][0]
        self.assertIn("Mira:", line)
        self.assertIn("completed", line.lower())
        self.assertNotIn("terminal", line.lower())
        self.assertNotIn("sqlite", line.lower())
        self.assertNotIn("/home/", line)

    def test_lead_rollup_keeps_readable_headline_and_plan(self) -> None:
        from app.kairo.operator_deterministic_report import compose_operator_report

        headline = (
            "Priya completed the classroom workflow and verified the teacher handoff."
        )
        lead_next = "Run the focused browser check, then ship the verified change."
        composed = compose_operator_report(
            {
                "workspace_id": "workspace_dashpro",
                "briefing": _MOCK_BRIEFING,
                "fleet": _MOCK_FLEET,
                "roster": {"busy": [], "completed": [], "failed": [], "employees": []},
                "handoffs": [
                    {
                        "lead_name": "Dana",
                        "headline": headline,
                        "lead_next": lead_next,
                    }
                ],
                "top_signals": [],
                "active_runs": [],
                "pending_approvals": 0,
                "awaiting_engagement_count": 0,
                "next_safe_actions": [],
                "fingerprint": "complete-rollup",
            }
        )

        line = composed["sections"]["lead_rollups"][0]
        self.assertIn("Priya completed the classroom workflow", line)
        self.assertIn("focused browser check", line)
        self.assertLessEqual(len(line), 220)

    def test_next_move_preserves_promised_workspace_switch(self) -> None:
        from app.kairo.operator_deterministic_report import compose_operator_report

        composed = compose_operator_report(
            {
                "briefing": {
                    **_MOCK_BRIEFING,
                    "advise": (
                        "Critical signal in axon-watch needs review; "
                        "switch there before continuing."
                    ),
                },
                "fleet": _MOCK_FLEET,
                "roster": {"busy": [], "completed": [], "failed": [], "employees": []},
                "handoffs": [],
                "top_signals": [],
                "active_runs": [],
                "pending_approvals": 0,
                "awaiting_engagement_count": 0,
                "next_safe_actions": [],
                "fingerprint": "switch-workspace",
            }
        )

        self.assertEqual(
            "I'll switch to axon-watch and start that investigation next",
            composed["sections"]["next_move"],
        )

    def test_lead_rollup_scrubs_ask_option_and_push_laundry(self) -> None:
        from app.kairo.operator_deterministic_report import compose_operator_report

        composed = compose_operator_report(
            {
                "workspace_id": "workspace_dashpro",
                "briefing": _MOCK_BRIEFING,
                "fleet": _MOCK_FLEET,
                "roster": {"busy": [], "completed": [], "failed": [], "employees": []},
                "handoffs": [
                    {
                        "lead_name": "Dana",
                        "headline": (
                            "Dana (lead) completed. Committed successfully with message: "
                            "Selected option 1: Yes. Push failed: git push failed"
                        ),
                        "lead_next": "",
                    }
                ],
                "top_signals": [],
                "active_runs": [],
                "pending_approvals": 0,
                "awaiting_engagement_count": 0,
                "next_safe_actions": [],
                "fingerprint": "push-laundry",
            }
        )

        line = composed["sections"]["lead_rollups"][0]
        self.assertIn("Dana:", line)
        self.assertIn("Committed after your choice", line)
        self.assertIn("push did not", line.lower())
        self.assertNotIn("Selected option", line)
        self.assertNotIn("Push failed: git push failed", line)

    def test_next_move_prefers_push_failure_over_stale_switch_advise(self) -> None:
        from app.kairo.operator_deterministic_report import compose_operator_report

        composed = compose_operator_report(
            {
                "briefing": {
                    **_MOCK_BRIEFING,
                    "advise": (
                        "Critical signal in axon-watch needs review; "
                        "switch there before continuing."
                    ),
                },
                "fleet": _MOCK_FLEET,
                "roster": {"busy": [], "completed": [], "failed": [], "employees": []},
                "handoffs": [
                    {
                        "lead_name": "Dana",
                        "headline": (
                            "Dana (lead) completed. Committed successfully with message: "
                            "Selected option 1: Yes. Push failed: git push failed"
                        ),
                        "lead_next": "",
                    }
                ],
                "top_signals": [],
                "active_runs": [],
                "pending_approvals": 0,
                "awaiting_engagement_count": 0,
                "next_safe_actions": [],
                "fingerprint": "push-over-switch",
            }
        )

        self.assertIn("inspect the exact push error", composed["sections"]["next_move"].lower())
        self.assertNotIn("switch to axon-watch", composed["sections"]["next_move"].lower())

    def test_next_move_uses_non_fast_forward_stderr(self) -> None:
        from app.kairo.operator_deterministic_report import compose_operator_report

        composed = compose_operator_report(
            {
                "briefing": _MOCK_BRIEFING,
                "fleet": _MOCK_FLEET,
                "roster": {"busy": [], "completed": [], "failed": [], "employees": []},
                "handoffs": [
                    {
                        "lead_name": "Dana",
                        "headline": (
                            "Committed successfully. Push failed: git push failed: "
                            "updates were rejected (non-fast-forward); fetch first"
                        ),
                        "lead_next": "",
                    }
                ],
                "top_signals": [],
                "active_runs": [],
                "pending_approvals": 0,
                "awaiting_engagement_count": 0,
                "next_safe_actions": [],
                "fingerprint": "push-non-fast-forward",
            }
        )

        self.assertEqual(
            "I'll open the Lead receipt, sync the branch safely, then retry the push",
            composed["sections"]["next_move"],
        )
        self.assertIn(
            "remote branch is ahead",
            composed["sections"]["lead_rollups"][0].lower(),
        )

    def test_next_move_uses_authentication_stderr(self) -> None:
        from app.kairo.operator_deterministic_report import compose_operator_report

        composed = compose_operator_report(
            {
                "briefing": _MOCK_BRIEFING,
                "fleet": _MOCK_FLEET,
                "roster": {"busy": [], "completed": [], "failed": [], "employees": []},
                "handoffs": [
                    {
                        "lead_name": "Dana",
                        "headline": (
                            "Committed successfully. Push failed: git push failed: "
                            "remote: HTTP 403 permission denied"
                        ),
                        "lead_next": "",
                    }
                ],
                "top_signals": [],
                "active_runs": [],
                "pending_approvals": 0,
                "awaiting_engagement_count": 0,
                "next_safe_actions": [],
                "fingerprint": "push-auth",
            }
        )

        self.assertEqual(
            "I'll open the Lead receipt, restore Git credentials, then retry the push",
            composed["sections"]["next_move"],
        )

    def test_next_move_prefers_vault_for_github_probe_signal(self) -> None:
        from app.kairo.operator_deterministic_report import compose_operator_report

        composed = compose_operator_report(
            {
                "briefing": {
                    **_MOCK_BRIEFING,
                    "advise": (
                        "Critical signal in axon-watch needs review; "
                        "switch there before continuing."
                    ),
                },
                "fleet": _MOCK_FLEET,
                "roster": {"busy": [], "completed": [], "failed": [], "employees": []},
                "handoffs": [],
                "top_signals": [
                    {
                        "title": "DashPro GitHub API warning",
                        "summary": "HTTP 401 — invalid or placeholder probe token",
                        "severity": "high",
                    }
                ],
                "active_runs": [],
                "pending_approvals": 0,
                "awaiting_engagement_count": 0,
                "next_safe_actions": [],
                "fingerprint": "github-vault",
            }
        )

        self.assertEqual(
            "I'll open Vault and restore the GitHub probe token next",
            composed["sections"]["next_move"],
        )

    @patch(_GRAPH_PATCH, return_value=_MOCK_GRAPH)
    @patch(_FLEET_PATCH, return_value=_MOCK_FLEET)
    @patch(_BRIEFING_PATCH, return_value=_MOCK_BRIEFING)
    @patch("app.kairo_conversation.dispatch_ide_composer")
    def test_converse_report_uses_deterministic_lane_not_lane_b(
        self,
        mock_dispatch,
        *_mocks: object,
    ) -> None:
        from app.kairo_conversation import converse_turn

        with patch(
            "app.kairo.operator_deterministic_report._roster_snapshot",
            return_value={
                "workspace_id": "workspace_dashpro",
                "company_name": "DashPro",
                "employees": [],
                "busy": [
                    {
                        "employee_id": "emp_dana",
                        "name": "Dana",
                        "role": "lead",
                        "role_label": "Lead",
                        "status": "executing",
                        "active_run_id": "run_dana_1",
                    }
                ],
                "completed": [],
                "failed": [],
            },
        ):
            payload = converse_turn(
                content="REPORT",
                session_id="report-lane-session",
                workspace_id="workspace_dashpro",
                use_runtime=True,
                answer_tier="fast",
            )
        self.assertEqual("status_question", payload["turn_kind"])
        self.assertEqual("template", payload["source"])
        self.assertEqual("deterministic_report", payload.get("dispatch_lane"))
        reply = str(payload["reply"])
        self.assertIn("Dana", reply)
        # Spoken normalization turns "Attention:" into "Attention,".
        self.assertRegex(reply, r"Attention[,:]")
        self.assertRegex(reply, r"Work in flight[,:]")
        report = payload.get("report")
        self.assertIsInstance(report, dict)
        sections = report.get("sections") if isinstance(report, dict) else None
        self.assertIsInstance(sections, dict)
        assert isinstance(sections, dict)
        self.assertTrue(
            any("Dana" in str(item) for item in (sections.get("work_in_flight") or [])),
        )
        mock_dispatch.assert_not_called()

    def test_compose_prioritizes_public_tunnel_restart_when_ingress_soft(self) -> None:
        from app.kairo.operator_deterministic_report import compose_operator_report

        briefing = {
            **_MOCK_BRIEFING,
            "advise": "Inspect Axon-X GitHub API warning",
            "degraded": {
                "active": True,
                "reasons": [
                    "remote ingress · Network unreachable on https://axon.edudashpro.org.za/api/health"
                ],
            },
        }
        composed = compose_operator_report(
            {
                "workspace_id": "workspace_axon_watch",
                "briefing": briefing,
                "fleet": _MOCK_FLEET,
                "roster": {"busy": [], "completed": [], "failed": [], "employees": []},
                "handoffs": [],
                "top_signals": [],
                "active_runs": [],
                "pending_approvals": 0,
                "awaiting_engagement_count": 0,
                "next_safe_actions": [],
                "fingerprint": "tunnel-soft",
            }
        )
        attention = " ".join(composed["sections"]["attention"]).lower()
        self.assertIn("public tunnel", attention)
        self.assertIn("restart", attention)
        self.assertEqual(
            "I'll restart the public tunnel next",
            composed["sections"]["next_move"],
        )


if __name__ == "__main__":
    unittest.main()
