"""Deterministic REPORT — next-move selection regression tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

from tests.support.control_plane_app_loader import prepare_control_plane_imports

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


class OperatorDeterministicReportNextMoveTests(unittest.TestCase):
    def setUp(self) -> None:
        self._saved = prepare_control_plane_imports()
        self.addCleanup(self._restore)

    def _restore(self) -> None:
        for name in list(sys.modules):
            if name == "app" or name.startswith("app."):
                del sys.modules[name]
        sys.modules.update(self._saved)

    def test_next_move_preserves_vaxon_attendance(self) -> None:
        from app.kairo.operator_deterministic_report import compose_operator_report

        composed = compose_operator_report(
            {
                "briefing": {
                    **_MOCK_BRIEFING,
                    "advise": (
                        "VAXON is attending the critical signal in axon-watch; "
                        "keep working here."
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
            "VAXON is investigating axon-watch and will report back here",
            composed["sections"]["next_move"],
        )

    def test_next_move_prefers_push_failure_over_stale_switch_advise(self) -> None:
        from app.kairo.operator_deterministic_report import compose_operator_report

        composed = compose_operator_report(
            {
                "briefing": {
                    **_MOCK_BRIEFING,
                    "advise": (
                        "VAXON is attending the critical signal in axon-watch; "
                        "keep working here."
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
        self.assertNotIn("attending the signal", composed["sections"]["next_move"].lower())

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
                        "VAXON is attending the critical signal in axon-watch; "
                        "keep working here."
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
                "fingerprint": "github-probe",
            }
        )

        self.assertEqual(
            "I'll open Vault and restore the GitHub probe token next",
            composed["sections"]["next_move"],
        )

    def test_next_move_assigns_generic_signal_investigation_to_vaxon(self) -> None:
        from app.kairo.operator_deterministic_report import compose_operator_report

        composed = compose_operator_report(
            {
                "briefing": _MOCK_BRIEFING,
                "fleet": _MOCK_FLEET,
                "roster": {"busy": [], "completed": [], "failed": [], "employees": []},
                "handoffs": [],
                "top_signals": [
                    {
                        "title": "Fast Gate failed",
                        "summary": "A contract check failed",
                        "severity": "high",
                    }
                ],
                "active_runs": [],
                "pending_approvals": 0,
                "awaiting_engagement_count": 0,
                "next_safe_actions": [],
                "fingerprint": "generic-investigation",
            }
        )

        self.assertEqual(
            "VAXON is investigating Fast Gate failed and will report back here",
            composed["sections"]["next_move"],
        )

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
