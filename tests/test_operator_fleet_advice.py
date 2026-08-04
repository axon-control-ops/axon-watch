from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.operator_briefing_rhythm import build_briefing_advise  # noqa: E402
from app.operator_fleet_advice import (  # noqa: E402
    build_fleet_advice_pack,
    build_fleet_coach_line,
    resolve_fleet_briefing_advise,
    select_fleet_advice_winner,
    workspace_advice_label,
)


class OperatorFleetAdviceTests(unittest.TestCase):
    def test_idle_fleet_pack_has_no_winner(self) -> None:
        pack = build_fleet_advice_pack(
            active_run_records=[],
            pending_approval_records=[],
            fleet_signals=[],
            degraded={"active": False, "reasons": []},
            watch_connected=True,
            scope_mode="fleet",
        )
        self.assertEqual([], pack["facts"])
        self.assertIsNone(pack["winner"])
        self.assertIsNone(resolve_fleet_briefing_advise(pack=pack))

    def test_ranking_prefers_approval_over_critical_signal(self) -> None:
        pack = build_fleet_advice_pack(
            active_run_records=[],
            pending_approval_records=[
                {
                    "run_id": "run_hot",
                    "workspace_id": "workspace_dashpro",
                    "summary": "Guarded deploy",
                }
            ],
            fleet_signals=[
                {
                    "signal_id": "sig_crit",
                    "workspace_id": "workspace_alpha",
                    "title": "Disk full",
                    "severity": "critical",
                    "status": "open",
                }
            ],
            degraded={"active": True, "reasons": ["watch probe failed"]},
            watch_connected=False,
            display_names={"workspace_dashpro": "DashPro"},
            scope_mode="fleet",
        )
        winner = pack["winner"]
        assert winner is not None
        self.assertEqual("pending_approval", winner["kind"])
        self.assertEqual("DashPro", winner["display_name"])

    def test_quiet_focus_redirects_to_hot_workspace_approval(self) -> None:
        pack = build_fleet_advice_pack(
            active_run_records=[],
            pending_approval_records=[
                {
                    "run_id": "run_hot",
                    "workspace_id": "workspace_dashpro",
                    "summary": "Guarded deploy",
                }
            ],
            fleet_signals=[],
            degraded={"active": False, "reasons": []},
            watch_connected=True,
            display_names={
                "workspace_dashpro": "DashPro",
                "workspace_alpha": "axon-watch",
            },
            focused_workspace_id="workspace_alpha",
            scope_mode="workspace",
        )
        advise = build_briefing_advise(
            next_safe_actions=[],
            active_runs=[],
            fleet_advice_pack=pack,
            display_names={
                "workspace_dashpro": "DashPro",
                "workspace_alpha": "axon-watch",
            },
        )
        self.assertEqual(
            "Approve the guarded run in DashPro before starting more axon-watch work.",
            advise,
        )

    def test_quiet_focus_redirects_to_critical_signal(self) -> None:
        pack = build_fleet_advice_pack(
            active_run_records=[],
            pending_approval_records=[],
            fleet_signals=[
                {
                    "signal_id": "sig_crit",
                    "workspace_id": "workspace_local",
                    "title": "Fast Gate failed",
                    "severity": "high",
                    "status": "open",
                }
            ],
            degraded={"active": False, "reasons": []},
            watch_connected=True,
            display_names={"workspace_local": "axon-local"},
            focused_workspace_id="workspace_alpha",
            scope_mode="workspace",
        )
        line = resolve_fleet_briefing_advise(pack=pack)
        self.assertEqual(
            "VAXON is attending the critical signal in axon-local; keep working here.",
            line,
        )

    def test_focused_local_winner_keeps_next_safe_action_copy(self) -> None:
        pack = build_fleet_advice_pack(
            active_run_records=[
                {
                    "run_id": "run_local",
                    "workspace_id": "workspace_alpha",
                    "phase": "awaiting_approval",
                    "can_approve": True,
                    "summary": "Local guarded run",
                }
            ],
            pending_approval_records=[],
            fleet_signals=[],
            degraded={"active": False, "reasons": []},
            watch_connected=True,
            focused_workspace_id="workspace_alpha",
            scope_mode="workspace",
        )
        self.assertIsNone(resolve_fleet_briefing_advise(pack=pack))
        advise = build_briefing_advise(
            next_safe_actions=[
                {
                    "kind": "approve_run",
                    "title": "Approve guarded run",
                    "detail": "Approve Local guarded run to continue execution.",
                }
            ],
            active_runs=[],
            fleet_advice_pack=pack,
        )
        self.assertEqual("Approve Local guarded run to continue execution.", advise)

    def test_fleet_scope_names_hot_workspace(self) -> None:
        pack = build_fleet_advice_pack(
            active_run_records=[
                {
                    "run_id": "run_ready",
                    "workspace_id": "workspace_finance",
                    "phase": "review_ready",
                    "summary": "Ledger check",
                }
            ],
            pending_approval_records=[],
            fleet_signals=[],
            degraded={"active": False, "reasons": []},
            watch_connected=True,
            display_names={"workspace_finance": "Finance"},
            scope_mode="fleet",
        )
        line = build_fleet_coach_line(pack["winner"], scope_mode="fleet")
        self.assertEqual("Review the ready run in Finance.", line)

    def test_github_api_warning_advise_points_at_vault(self) -> None:
        line = build_fleet_coach_line(
            {
                "kind": "critical_signal",
                "workspace_id": "workspace_dashpro",
                "title": "DashPro GitHub API warning",
                "summary": "HTTP 401 — invalid or placeholder probe token",
            },
            focused_workspace_id="workspace_alpha",
            scope_mode="workspace",
            display_names={"workspace_dashpro": "DashPro"},
        )
        self.assertIn("Vault", line)
        self.assertIn("GH_TOKEN", line)

    def test_generic_github_warning_does_not_invent_token_failure(self) -> None:
        line = build_fleet_coach_line(
            {
                "kind": "critical_signal",
                "workspace_id": "workspace_dashpro",
                "title": "DashPro GitHub API warning",
                "summary": "API rate limit is low",
            },
            focused_workspace_id="workspace_alpha",
            scope_mode="workspace",
            display_names={"workspace_dashpro": "DashPro"},
        )
        self.assertNotIn("GH_TOKEN", line)
        self.assertEqual(
            "VAXON is attending the critical signal in DashPro; keep working here.",
            line,
        )

    def test_same_rank_prefers_focused_workspace(self) -> None:
        winner = select_fleet_advice_winner(
            [
                {
                    "kind": "pending_approval",
                    "rank": 1,
                    "workspace_id": "workspace_zeta",
                },
                {
                    "kind": "pending_approval",
                    "rank": 1,
                    "workspace_id": "workspace_alpha",
                },
            ],
            focused_workspace_id="workspace_alpha",
        )
        assert winner is not None
        self.assertEqual("workspace_alpha", winner["workspace_id"])

    def test_workspace_label_falls_back_to_readable_id(self) -> None:
        self.assertEqual("DashPro", workspace_advice_label("workspace_x", {"workspace_x": "DashPro"}))
        self.assertEqual("Alpha", workspace_advice_label("workspace_alpha"))

    def test_open_handoff_ranks_above_degraded_runtime(self) -> None:
        pack = build_fleet_advice_pack(
            active_run_records=[],
            pending_approval_records=[],
            fleet_signals=[],
            degraded={"active": True, "reasons": ["watch probe failed"]},
            watch_connected=False,
            display_names={"workspace_dashpro": "DashPro"},
            focused_workspace_id="workspace_alpha",
            scope_mode="workspace",
            open_handoffs=[
                {
                    "handoff_id": "handoff-1",
                    "source_workspace_id": "workspace_alpha",
                    "target_workspace_id": "workspace_dashpro",
                    "task": "Finish DashPro follow-up",
                    "status": "routed",
                    "target_task_id": "task-1",
                }
            ],
        )
        winner = pack["winner"]
        assert winner is not None
        self.assertEqual("open_handoff", winner["kind"])
        advise = resolve_fleet_briefing_advise(
            pack=pack,
            display_names={
                "workspace_dashpro": "DashPro",
                "workspace_alpha": "axon-watch",
            },
        )
        self.assertEqual(
            "VAXON owns the open handoff in DashPro: “Finish DashPro follow-up”."
            " Keep working in axon-watch; VAXON will report the outcome here.",
            advise,
        )
        from app.operator_fleet_advice import build_advise_ui_action

        action = build_advise_ui_action(
            winner,
            focused_workspace_id="workspace_alpha",
        )
        self.assertEqual("switch_workspace", action["type"])
        self.assertEqual("workspace_dashpro", action["workspace_id"])
        self.assertTrue(action["focus_attention"])

    def test_open_handoff_advice_keeps_the_complete_task(self) -> None:
        task = (
            "DashPro PostHog warning, PostHog API query failed, "
            "The read operation timed out while loading project insights"
        )
        pack = build_fleet_advice_pack(
            active_run_records=[],
            pending_approval_records=[],
            fleet_signals=[],
            degraded={"active": False, "reasons": []},
            watch_connected=True,
            display_names={"workspace_dashpro": "DashPro"},
            focused_workspace_id="workspace_axon_watch",
            scope_mode="workspace",
            open_handoffs=[
                {
                    "handoff_id": "handoff-long-task",
                    "source_workspace_id": "workspace_axon_watch",
                    "target_workspace_id": "workspace_dashpro",
                    "task": task,
                    "status": "routed",
                    "target_task_id": "task-long",
                }
            ],
        )

        advise = resolve_fleet_briefing_advise(
            pack=pack,
            display_names={
                "workspace_dashpro": "DashPro",
                "workspace_axon_watch": "Axon Watch",
            },
        )

        self.assertIn(f"finish “{task}”", advise)
        self.assertNotIn("…", advise)


if __name__ == "__main__":
    unittest.main()
