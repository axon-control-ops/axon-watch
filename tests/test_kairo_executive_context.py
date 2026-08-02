from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.kairo_executive_context import build_executive_context_blocks  # noqa: E402
from app.kairo_conversation_runtime_context import build_runtime_context_block  # noqa: E402


class KairoExecutiveContextTests(unittest.TestCase):
    def test_projects_verified_intent_and_mission_memory(self) -> None:
        plan = {
            "plan_id": "lead-plan-1",
            "goal": "Harden authentication",
            "status": "completed",
            "mode": "fan_out",
            "plan": {
                "items": [
                    {
                        "owner_role": "frontend",
                        "goal": "Build login UI",
                    },
                    {
                        "owner_role": "backend",
                        "goal": "Implement session API",
                    },
                ]
            },
            "receipts": [
                {
                    "kind": "lead_synthesis_completed",
                    "payload": {"findings": ["Reuse the typed auth contract."]},
                }
            ],
        }
        pack = {
            "briefing": {
                "advise": "Review the authentication evidence.",
                "top_signals": [{"title": "Login error rate elevated"}],
                "degraded": {"active": True, "reasons": ["Auth service degraded"]},
                "pending_approvals": {"count": 1},
                "cli_runtime": {"blockers": ["Cursor authentication expired"]},
            }
        }

        with (
            patch(
                "app.kairo_executive_context._safe_recent_plans",
                return_value=[plan],
            ),
            patch(
                "app.kairo_executive_context._safe_presence_settings",
                return_value={
                    "autonomy_mode": "semi",
                    "voice_routing_mode": "runtime_on_deep",
                    "operator_persona_enabled": True,
                },
            ),
        ):
            block = "\n".join(
                build_executive_context_blocks(
                    workspace_id="workspace_axon_watch",
                    pack=pack,
                )
            )

        self.assertIn("ExecutiveIntent:", block)
        self.assertIn("Current Priority: Review the authentication evidence.", block)
        self.assertIn("MissionMemory:", block)
        self.assertIn("lead-plan-1 [completed] Harden authentication", block)
        self.assertIn("Reuse the typed auth contract.", block)
        self.assertIn("fan_out via backend + frontend", block)
        self.assertIn("Mission ID; Mission Title; Objective", block)
        self.assertIn("Planned; Dispatched; Observed; Verified; Completed", block)
        self.assertIn("Planner=Lead", block)

    def test_missing_context_is_labeled_unknown(self) -> None:
        with (
            patch("app.kairo_executive_context._safe_recent_plans", return_value=[]),
            patch(
                "app.kairo_executive_context._safe_presence_settings",
                return_value={},
            ),
        ):
            block = "\n".join(
                build_executive_context_blocks(
                    workspace_id="workspace_axon_watch",
                    pack={"briefing": {}},
                )
            )

        self.assertIn("Current Milestone: unknown — no verified source", block)
        self.assertIn("Recent Missions: unknown — no verified source", block)
        self.assertIn("Repeated Failures: none evidenced", block)

    def test_runtime_context_includes_executive_projection(self) -> None:
        pack = {
            "briefing": {
                "scope": {"workspace_id": "workspace_axon_watch"},
                "pending_approvals": {"count": 0},
                "top_signals": [],
                "active_runs": [],
                "degraded": {"active": False, "reasons": []},
                "connectivity": {"watch_connected": True},
                "next_safe_actions": [],
                "cli_runtime": {"dispatch_ready": True, "blockers": []},
            },
            "workspace": {"workspace_id": "workspace_axon_watch"},
            "fleet": {},
        }
        with (
            patch(
                "app.kairo_conversation_runtime_context.build_lane_b_context_block",
                return_value="Base context",
            ),
            patch(
                "app.kairo_conversation_runtime_context.build_executive_context_blocks",
                return_value=["ExecutiveIntent:", "- Vision: verified"],
            ) as executive,
            patch(
                "app.kairo_conversation_runtime_context.get_active_participant",
                return_value=None,
            ),
        ):
            context = build_runtime_context_block(
                content="Explain the current mission",
                workspace_id="workspace_axon_watch",
                pack=pack,
                session_id="session-eos",
                recent_turns=[],
            )

        self.assertIn("VAXON Executive Operating System contract:", context)
        self.assertIn("ExecutiveIntent:\n- Vision: verified", context)
        executive.assert_called_once_with(
            workspace_id="workspace_axon_watch",
            pack=pack,
        )


if __name__ == "__main__":
    unittest.main()
