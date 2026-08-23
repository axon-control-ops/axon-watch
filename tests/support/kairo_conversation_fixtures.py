"""Shared fixtures for KAIRO conversation turn tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[2] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.kairo.context_pack_cache import clear_pack_cache_for_tests  # noqa: E402
from app.kairo.turn_memory import clear_memory_for_tests  # noqa: E402
from tests.support.control_plane_db import isolate_workspace_bindings  # noqa: E402

MOCK_BRIEFING = {
    "generated_at": "2026-07-08T00:00:00Z",
    "notice": "Two runs are active.",
    "advise": "Review the top signal before dispatching more work.",
    "top_signals": [
        {
            "signal_id": "signal_monitor_dashpro_sentry_recent_issues_warning",
            "workspace_id": "workspace_dashpro",
            "title": "Sentry spike in DashPro",
            "summary": "3 unresolved issues",
            "severity": "high",
        }
    ],
    "pending_approvals": {"count": 2, "items": [{}, {}]},
    "active_runs": [{"run_id": "run_1", "summary": "Git status"}],
    "degraded": {"active": False, "reasons": []},
}
MOCK_FLEET = {
    "items": [
        {"workspace_id": "ws_a", "tone": "critical"},
        {"workspace_id": "ws_b", "tone": "nominal"},
    ]
}
MOCK_GRAPH = {"nodes": [{"node_id": "n1"}], "edges": []}

# Patches target where the pack builder imports symbols, not its facade.
BRIEFING_PATCH = "app.kairo.conversation_context_pack.build_operator_briefing"
FLEET_PATCH = "app.kairo.conversation_context_pack.build_operator_fleet_health"
GRAPH_PATCH = "app.kairo.conversation_context_pack.build_operator_brain_graph"


class KairoConversationTestCase(unittest.TestCase):
    def setUp(self) -> None:
        isolate_workspace_bindings(self)
        clear_pack_cache_for_tests()
        clear_memory_for_tests()
        runtime = patch(
            "app.kairo_conversation.dispatch_ide_composer",
            return_value={
                "content": "",
                "dispatched": False,
                "runtime_id": "test_runtime",
                "runtime_label": "Test runtime",
                "reason": "unit-test runtime disabled",
            },
        )
        runtime.start()
        self.addCleanup(runtime.stop)
