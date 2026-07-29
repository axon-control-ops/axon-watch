"""REPORT freshness — drop healed auth failures and busy false-alarms."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))


class OperatorReportFreshnessTests(unittest.TestCase):
    def test_failed_rows_skip_busy_and_healed_auth(self) -> None:
        from app.kairo.operator_deterministic_report import _failed_rows

        rows = [
            {
                "name": "Reed",
                "role": "backend",
                "last_outcome": "failed",
                "active_run_id": "run_live",
                "last_outcome_detail": "Cursor auth probe timed out",
            },
            {
                "name": "Mira",
                "role": "lead",
                "last_outcome": "failed",
                "active_run_id": "",
                "last_outcome_detail": "no CLI runtime is ready. Open Runtime or Vault, then retry",
            },
            {
                "name": "Rowan",
                "role": "watcher",
                "last_outcome": "failed",
                "active_run_id": "",
                "last_outcome_detail": "CI failed on main",
            },
        ]
        failed = _failed_rows(rows, dispatch_ready=True)
        self.assertEqual(["Rowan"], [row["name"] for row in failed])

    def test_fresh_handoffs_drop_healed_cli_rollups(self) -> None:
        from app.kairo.operator_deterministic_report import _fresh_handoffs

        handoffs = [
            {
                "receipt_id": "r1",
                "employee_name": "Mira",
                "headline": "Mira cannot start. no CLI runtime is ready. Open Runtime or Vault, then retry",
                "lead_summary": "no CLI runtime is ready",
                "lead_next": "",
            },
            {
                "receipt_id": "r2",
                "employee_name": "Mira",
                "headline": "Mira completed CI repair",
                "lead_summary": "CI repair landed",
                "lead_next": "watch Fast Gate",
            },
        ]
        fresh = _fresh_handoffs(handoffs, dispatch_ready=True)
        self.assertEqual(1, len(fresh))
        self.assertIn("CI repair", fresh[0]["headline"])

    def test_compose_omits_healed_cli_rollup_lines(self) -> None:
        from app.kairo.operator_deterministic_report import compose_operator_report

        briefing = {
            "scope": {"workspace_id": "workspace_axon_watch", "display_name": "Axon Watch"},
            "notice": "",
            "advise": "Keep watching",
            "pending_approvals": {"count": 0},
            "top_signals": [],
            "active_runs": [],
            "next_safe_actions": [],
            "awaiting_engagement_count": 0,
            "degraded": {"active": False},
            "cli_runtime": {"dispatch_ready": True, "blockers": []},
        }
        composed = compose_operator_report(
            {
                "workspace_id": "workspace_axon_watch",
                "briefing": briefing,
                "fleet": {"workspace_count": 1, "critical_count": 0, "attention_count": 0},
                "roster": {
                    "busy": [],
                    "completed": [{"name": "Jules", "role": "frontend", "role_label": "Frontend"}],
                    "failed": [],
                    "employees": [],
                },
                "handoffs": [
                    {
                        "receipt_id": "old",
                        "employee_name": "Mira",
                        "from_name": "Mira",
                        "headline": "cannot start. no CLI runtime is ready",
                        "lead_summary": "no CLI runtime is ready",
                        "lead_next": "",
                    }
                ],
                "top_signals": [],
                "active_runs": [],
                "pending_approvals": 0,
                "awaiting_engagement_count": 0,
                "next_safe_actions": [],
                "fingerprint": "fresh-auth",
            }
        )
        rollups = " ".join(composed["sections"]["lead_rollups"]).lower()
        self.assertNotIn("no cli runtime is ready", rollups)


if __name__ == "__main__":
    unittest.main()
