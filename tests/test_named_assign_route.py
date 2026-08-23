from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTROL_PLANE_ROOT = REPO_ROOT / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.chat.lane_b_lead_named_assign_fast_path import (  # noqa: E402
    maybe_post_lead_named_assign_message,
)
from app.workspace_agents.named_assign_route import (  # noqa: E402
    is_vague_named_assign,
    match_named_assign_employee,
    named_assign_action_body,
    rewrite_named_assign_prompt,
)
from app.workspace_agents.teammate_route import TeammateRouteEmployee  # noqa: E402


def _roster() -> list[TeammateRouteEmployee]:
    return [
        TeammateRouteEmployee(
            employee_id="employee-lead",
            name="Imani",
            role="lead",
            role_label="Lead",
            owns="priorities",
        ),
        TeammateRouteEmployee(
            employee_id="employee-backend",
            name="Cole",
            role="backend",
            role_label="Backend",
            owns="APIs",
        ),
        TeammateRouteEmployee(
            employee_id="employee-frontend",
            name="Lila",
            role="frontend",
            role_label="Frontend",
            owns="UI",
        ),
        TeammateRouteEmployee(
            employee_id="employee-watcher",
            name="Rowan",
            role="watcher",
            role_label="Watcher",
            owns="signals",
        ),
    ]


class NamedAssignRouteTests(unittest.TestCase):
    def test_matches_all_named_specialists(self) -> None:
        roster = _roster()
        cases = [
            ("Ok assign Cole the task and have him report back", "Cole"),
            ("Have Lila polish the enrollment card", "Lila"),
            ("@Rowan watch the red-build alerts", "Rowan"),
            ("Give Cole the Lesego login wiring", "Cole"),
        ]
        for prompt, expected in cases:
            with self.subTest(prompt=prompt):
                match = match_named_assign_employee(prompt, roster)
                self.assertIsNotNone(match)
                assert match is not None
                self.assertEqual(expected, match.name)

    def test_rewrite_strips_assign_framing(self) -> None:
        rewritten = rewrite_named_assign_prompt(
            "Ok assign Cole the Lesego login table and have him report back",
            "Cole",
        )
        self.assertIn("You own this assignment from Lead", rewritten)
        self.assertNotIn("assign Cole", rewritten.lower())
        self.assertIn("Lesego login table", rewritten)

    def test_vague_named_assign_has_no_concrete_body(self) -> None:
        self.assertIsNone(named_assign_action_body("Route the task to Lila", "Lila"))
        self.assertTrue(is_vague_named_assign("Route the task to Lila", "Lila"))
        rewritten = rewrite_named_assign_prompt("Route the task to Lila", "Lila")
        self.assertIn("did not include a concrete task body", rewritten)

    def test_lead_fast_path_materializes_concrete_named_assign(self) -> None:
        roster = _roster()
        saved: list[dict] = []

        def save_message(payload: dict) -> dict:
            saved.append(payload)
            return payload

        with patch(
            "app.chat.lane_b_lead_named_assign_fast_path.build_company_roster",
            return_value={"employees": [row.__dict__ for row in roster]},
        ), patch(
            "app.chat.lane_b_lead_named_assign_fast_path._create_named_handoff_task",
            return_value={
                "task": {"task_id": "task-concrete"},
                "run": {"run_id": "run-concrete", "phase": "executing"},
                "started": True,
            },
        ):
            response = maybe_post_lead_named_assign_message(
                workspace_id="workspace_test",
                content="Ok assign Cole the Lesego login table and have him report back",
                thread_id="thread_lead",
                employee_role="lead",
                lead_name="Imani",
                composer_mode="agent",
                created_at="2026-07-29T12:00:00Z",
                save_message=save_message,
                new_message_id=lambda prefix: f"{prefix}_1",
                bind_attachments=lambda _message_id: [],
            )

        self.assertIsNotNone(response)
        assert response is not None
        self.assertTrue(response["dispatched"])
        self.assertEqual("run-concrete", response["run_id"])
        self.assertEqual("task-concrete", response["named_assign"]["task_id"])
        self.assertFalse(response["streaming"])
        self.assertEqual("Cole", response["named_assign"]["employee_name"])
        agent = next(row for row in saved if row["role"] == "agent")
        self.assertIn("routed a concrete Lead handoff to Cole", agent["content"])
        self.assertIn("Lesego login table", agent["content"])

    def test_lead_fast_path_does_not_recover_stale_operator_ask(self) -> None:
        roster = _roster()
        saved: list[dict] = []

        def save_message(payload: dict) -> dict:
            saved.append(payload)
            return payload

        with patch(
            "app.chat.lane_b_lead_named_assign_fast_path.build_company_roster",
            return_value={"employees": [row.__dict__ for row in roster]},
        ), patch(
            "app.persistence.chat_store.list_thread_messages",
            return_value=[
                {
                    "role": "operator",
                    "content": "Fix the parent dashboard submission screen copy and teacher review flow",
                },
                {"role": "operator", "content": "Route the task to Lila"},
            ],
        ), patch(
            "app.chat.lane_b_lead_named_assign_fast_path._create_named_handoff_task",
        ) as create_task:
            response = maybe_post_lead_named_assign_message(
                workspace_id="workspace_test",
                content="Route the task to Lila",
                thread_id="thread_lead",
                employee_role="lead",
                lead_name="Imani",
                composer_mode="agent",
                created_at="2026-07-29T12:00:00Z",
                save_message=save_message,
                new_message_id=lambda prefix: f"{prefix}_1",
                bind_attachments=lambda _message_id: [],
            )

        self.assertIsNotNone(response)
        assert response is not None
        self.assertEqual("", response["named_assign"]["task_id"])
        self.assertFalse(response["dispatched"])
        create_task.assert_not_called()
        agent = next(row for row in saved if row["role"] == "agent")
        self.assertIn("send the exact goal/acceptance criteria", agent["content"])

    def test_lead_fast_path_skips_when_assigning_lead(self) -> None:
        roster = _roster()
        with patch(
            "app.chat.lane_b_lead_named_assign_fast_path.build_company_roster",
            return_value={"employees": [row.__dict__ for row in roster]},
        ):
            response = maybe_post_lead_named_assign_message(
                workspace_id="workspace_test",
                content="Assign Imani the triage priorities",
                thread_id="thread_lead",
                employee_role="lead",
                lead_name="Imani",
                composer_mode="agent",
                created_at="2026-07-29T12:00:00Z",
                save_message=Mock(),
                new_message_id=lambda prefix: f"{prefix}_1",
                bind_attachments=lambda _message_id: [],
            )
        self.assertIsNone(response)

    def test_lead_fast_path_skips_multi_role_fan_out(self) -> None:
        roster = _roster()
        with patch(
            "app.chat.lane_b_lead_named_assign_fast_path.build_company_roster",
            return_value={"employees": [row.__dict__ for row in roster]},
        ):
            response = maybe_post_lead_named_assign_message(
                workspace_id="workspace_test",
                content=(
                    "The three tasks are still open. Assign the two UI tasks to "
                    "Lila (frontend) and the teacher query task to the backend "
                    "specialist now. Use materialize_lead_fan_out with "
                    "create_runs=True or directly lease those tasks."
                ),
                thread_id="thread_lead",
                employee_role="lead",
                lead_name="Imani",
                composer_mode="agent",
                created_at="2026-07-29T12:00:00Z",
                save_message=Mock(),
                new_message_id=lambda prefix: f"{prefix}_1",
                bind_attachments=lambda _message_id: [],
            )
        self.assertIsNone(response)


if __name__ == "__main__":
    unittest.main()
