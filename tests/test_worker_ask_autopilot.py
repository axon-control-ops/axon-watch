from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.workspace_agents.ask_autopilot import maybe_resolve_safe_ask, parse_latest_ask_card  # noqa: E402
from app.workspace_agents.worker_prompt import build_continuous_worker_prompt  # noqa: E402
from app.workspace_agents.config_loader import EmployeeConfig  # noqa: E402


class WorkerAskAutopilotTests(unittest.TestCase):
    def test_parses_latest_ask_card(self) -> None:
        parsed = parse_latest_ask_card(
            """
Done investigating.

:::ask How should I continue?
- 1 | Clear cache and retry
- 2 | Stop
:::
"""
        )

        assert parsed is not None
        prompt, options = parsed
        self.assertEqual("How should I continue?", prompt)
        self.assertEqual(["Clear cache and retry", "Stop"], [option.label for option in options])

    def test_auto_resolves_safe_reversible_engineering_choice(self) -> None:
        resolution = maybe_resolve_safe_ask(
            """
I found a likely stale dashboard path.

:::ask Which continuation should I take?
- 1 | Stale dev bundle/cache — cache clear/hard refresh first
- 2 | Testing account is K-12 parent — redirected to separate route
- 3 | Unsure — harden Fast Refresh reliability on teacher dashboard re-export barrel as precaution
:::

Confidence: 9/10
""",
            auto_mode_enabled=True,
        )

        assert resolution is not None
        self.assertEqual("3", resolution.option.id)
        self.assertIn("Selected option 3", resolution.answer_text)
        self.assertIn("auto", resolution.receipt_summary.lower())

    def test_auto_does_not_resolve_release_or_secret_choice(self) -> None:
        resolution = maybe_resolve_safe_ask(
            """
:::ask Should I deploy this to production?
- 1 | Deploy to production now
- 2 | Stop
:::
""",
            auto_mode_enabled=True,
        )

        self.assertIsNone(resolution)

        secret_resolution = maybe_resolve_safe_ask(
            """
:::ask Which credential should I use?
- 1 | Use the operator API token
- 2 | Create a new secret
:::
""",
            auto_mode_enabled=True,
        )

        self.assertIsNone(secret_resolution)

    def test_auto_disabled_does_not_resolve(self) -> None:
        resolution = maybe_resolve_safe_ask(
            """
:::ask How should I continue?
- 1 | Continue investigation
- 2 | Stop
:::
""",
            auto_mode_enabled=False,
        )

        self.assertIsNone(resolution)

    def test_worker_prompt_tells_agents_not_to_stop_on_safe_auto_asks(self) -> None:
        prompt = build_continuous_worker_prompt(
            workspace_id="workspace_dashpro",
            employee=EmployeeConfig(
                name="Priya",
                role="frontend",
                owns="UI",
                schedule="continuous",
            ),
            task={
                "task_id": "task-demo",
                "goal": "Fix the dashboard bug",
                "acceptance_criteria": "targeted check passes",
                "allowed_paths": ["app/", "components/"],
            },
        )

        self.assertIn("Auto-mode question discipline", prompt)
        self.assertIn("do not stop on ask cards for safe", prompt)
        self.assertIn("Only emit an Axon ask card for a real operator decision", prompt)


if __name__ == "__main__":
    unittest.main()
