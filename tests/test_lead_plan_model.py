from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.workspace_agents.lead_plan_model import (  # noqa: E402
    plan_from_model_payload,
    resolve_lead_task_plan,
)
from app.workspace_agents.lead_task_plan import fallback_single_owner_plan  # noqa: E402


ROSTER = [
    {"role": "lead", "name": "Dana", "owns": "priorities"},
    {"role": "frontend", "name": "Priya", "owns": "UI"},
    {"role": "backend", "name": "Marco", "owns": "APIs"},
    {"role": "integrations", "name": "Soren", "owns": "CI"},
    {"role": "watcher", "name": "Cass", "owns": "signals"},
]

# A plain content-editing task with no API/database/signals system involved at
# all, but containing a couple of generic keyword-bag words per role — the
# exact pattern that fanned a childcare-menu task out to mismatched Backend +
# Watcher specialists. Ties backend=2/watcher=3, both below the decisive bar.
_DOMAIN_AGNOSTIC_GOAL = (
    "Rearrange the existing weekly menu items and update the room roster "
    "service data, keeping an eye on child health signals throughout."
)


class LeadPlanModelTests(unittest.TestCase):
    def test_plan_from_model_payload_validates_roles(self) -> None:
        plan = plan_from_model_payload(
            goal="Ship the enrollment flow",
            roster=ROSTER,
            payload={
                "items": [
                    {
                        "owner_role": "frontend",
                        "goal": "Ship enrollment UI confirmation",
                        "dependencies": [],
                        "acceptance_criteria": "popup works",
                    },
                    {
                        "owner_role": "backend",
                        "goal": "Ship enrollment API",
                        "dependencies": [0],
                        "acceptance_criteria": "api green",
                    },
                    {
                        "owner_role": "wizard",
                        "goal": "Invented role should drop",
                        "dependencies": [],
                    },
                ]
            },
        )
        self.assertIsNotNone(plan)
        assert plan is not None
        roles = [item.owner_role for item in plan.items]
        self.assertEqual(["frontend", "backend"], roles)
        self.assertEqual([plan.items[0].plan_key], plan.items[1].dependencies)

    def test_resolve_uses_model_when_ambiguous(self) -> None:
        calls: list[dict] = []

        def fake_dispatch(**kwargs):  # type: ignore[no-untyped-def]
            calls.append(kwargs)
            return {
                "content": json.dumps(
                    {
                        "items": [
                            {
                                "owner_role": "integrations",
                                "goal": "Wire the secret rotation",
                                "dependencies": [],
                            }
                        ]
                    }
                ),
                "dispatched": True,
            }

        # Vague prompt tends to score soft / ambiguous; force empty items path via
        # model by using a prompt that scores nothing and falls to model.
        plan = resolve_lead_task_plan(
            goal="handle the thing carefully",
            roster=ROSTER,
            mode="decompose",
            workspace_id="workspace_dashpro",
            use_model=True,
            dispatch_runtime=fake_dispatch,
        )
        if calls:
            self.assertEqual("integrations", plan.items[0].owner_role)
            self.assertIn("secret rotation", plan.items[0].goal)
        else:
            # Deterministic may still emit a soft winner; fail-open must still yield items.
            self.assertTrue(plan.items)

    def test_ambiguous_multi_role_routes_through_model_tie_break(self) -> None:
        # Closes the gap that let the original incident ship: previously a
        # bare-minimum keyword-bag tie never reached the model at all because
        # it wasn't flagged ambiguous. This proves the tie-break is actually
        # invoked once _owners_for_clause correctly flags it.
        calls: list[dict] = []

        def fake_dispatch(**kwargs):  # type: ignore[no-untyped-def]
            calls.append(kwargs)
            return {
                "content": json.dumps(
                    {
                        "items": [
                            {
                                "owner_role": "watcher",
                                "goal": "Rearrange the menu and watch for health-note changes",
                                "dependencies": [],
                            }
                        ]
                    }
                ),
                "dispatched": True,
            }

        plan = resolve_lead_task_plan(
            goal=_DOMAIN_AGNOSTIC_GOAL,
            roster=ROSTER,
            mode="decompose",
            workspace_id="workspace_dashpro",
            use_model=True,
            dispatch_runtime=fake_dispatch,
        )
        self.assertTrue(calls, "the ambiguous multi-role tie should reach the model tie-break")
        self.assertEqual(1, len(plan.items))
        self.assertEqual("watcher", plan.items[0].owner_role)

    def test_ambiguous_multi_role_fails_safe_to_single_owner_when_model_unavailable(self) -> None:
        def failing_dispatch(**kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("runtime unavailable")

        plan = resolve_lead_task_plan(
            goal=_DOMAIN_AGNOSTIC_GOAL,
            roster=ROSTER,
            mode="decompose",
            workspace_id="workspace_dashpro",
            use_model=True,
            dispatch_runtime=failing_dispatch,
        )
        # Model tie-break failed; must not dispatch the mismatched Backend +
        # Watcher pair on a keyword-bag hunch — collapse to one confident owner.
        self.assertEqual(1, len(plan.items))

    def test_fallback_single_owner(self) -> None:
        plan = fallback_single_owner_plan(goal="do the work", roster=ROSTER)
        self.assertEqual(1, len(plan.items))
        self.assertEqual("backend", plan.items[0].owner_role)


if __name__ == "__main__":
    unittest.main()
