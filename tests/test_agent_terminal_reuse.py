"""Agent terminal sessions stay singleton per workspace."""

from __future__ import annotations

import unittest

from app.terminal.session_registry import (
    create_session,
    ensure_agent_session,
    list_sessions,
    reset_registry,
)


class AgentTerminalReuseTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_registry()

    def test_ensure_agent_session_reuses_one_tab_across_runs(self) -> None:
        first = ensure_agent_session(workspace_id="workspace_alpha", run_id="run_11111111")
        second = ensure_agent_session(workspace_id="workspace_alpha", run_id="run_22222222")
        self.assertEqual("terminal-agent", first.session_id)
        self.assertEqual(first.session_id, second.session_id)
        self.assertEqual("run_22222222", second.run_id)
        agent_tabs = [
            item for item in list_sessions("workspace_alpha") if item.role == "agent"
        ]
        self.assertEqual(1, len(agent_tabs))

    def test_create_session_agent_without_id_also_reuses(self) -> None:
        a = create_session(workspace_id="workspace_beta", role="agent", run_id="run_aaaa")
        b = create_session(workspace_id="workspace_beta", role="agent", run_id="run_bbbb")
        self.assertEqual("terminal-agent", a.session_id)
        self.assertEqual(a.session_id, b.session_id)


if __name__ == "__main__":
    unittest.main()
