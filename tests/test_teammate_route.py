from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from tests.support.control_plane_db import isolate_control_plane_db

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTROL_PLANE_ROOT = REPO_ROOT / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.main import app  # noqa: E402
from app.kairo.teammate_handoff import (  # noqa: E402
    build_specialty_task_action,
    enrich_handoff_with_teammate,
)
from app.persistence import run_store  # noqa: E402
from app.workspace_agents.teammate_route import (  # noqa: E402
    TeammateRouteDecision,
    TeammateRouteEmployee,
    apply_model_tiebreak,
    route_teammate_decision,
    should_soft_route_to_teammate,
)


def _fixture() -> dict[str, object]:
    path = REPO_ROOT / "packages/shared-types/fixtures/teammate-route-cases.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _roster() -> list[TeammateRouteEmployee]:
    rows = _fixture()["roster"]
    assert isinstance(rows, list)
    return [TeammateRouteEmployee(**row) for row in rows]


class TeammateRouteTests(unittest.TestCase):
    def test_python_scorer_matches_shared_golden_cases(self) -> None:
        fixture = _fixture()
        roster = _roster()
        by_id = {employee.employee_id: employee for employee in roster}
        cases = fixture["cases"]
        assert isinstance(cases, list)

        for case in cases:
            assert isinstance(case, dict)
            current_id = case.get("current_employee_id")
            current = by_id.get(str(current_id)) if current_id else None
            with self.subTest(case=case["id"]):
                decision = should_soft_route_to_teammate(
                    str(case["prompt"]),
                    current,
                    roster,
                )
                self.assertEqual(case["should_route"], decision.should_route)
                self.assertEqual(case["reason"], decision.reason)
                expected_employee = case.get("employee_id")
                if expected_employee:
                    self.assertIsNotNone(decision.employee)
                    assert decision.employee is not None
                    self.assertEqual(expected_employee, decision.employee.employee_id)

    def test_model_tiebreak_selects_only_a_roster_employee(self) -> None:
        roster = _roster()
        current = next(employee for employee in roster if employee.name == "Marco")
        base = TeammateRouteDecision(
            should_route=False,
            reason="margin_too_low",
            ambiguous=True,
            winner_score=1,
            second_score=1,
        )

        decision = apply_model_tiebreak(
            prompt="Fix the server UI",
            roster=roster,
            current_employee=current,
            base_decision=base,
            dispatch_runtime=lambda **_kwargs: {
                "content": json.dumps(
                    {
                        "employee_id": "employee-workspace_dashpro-frontend-2",
                        "role": "frontend",
                        "reason": "UI ownership",
                    }
                ),
                "dispatched": True,
                "runtime_id": "cursor",
                "runtime_model": "test-model",
            },
            workspace_id="workspace_dashpro",
        )

        self.assertTrue(decision.should_route)
        self.assertEqual("model_frontend", decision.reason)
        self.assertEqual("Priya", decision.employee.name if decision.employee else None)
        self.assertEqual("model", decision.source)

    def test_model_parse_failure_falls_back_to_no_route(self) -> None:
        roster = _roster()
        base = TeammateRouteDecision(
            should_route=False,
            reason="margin_too_low",
            ambiguous=True,
        )
        decision = apply_model_tiebreak(
            prompt="Fix the server UI",
            roster=roster,
            current_employee=None,
            base_decision=base,
            dispatch_runtime=lambda **_kwargs: {
                "content": "not-json",
                "dispatched": True,
            },
            workspace_id="workspace_dashpro",
        )
        self.assertFalse(decision.should_route)
        self.assertEqual("model", decision.source)
        self.assertEqual("model_tiebreak;parse_failed", decision.routing_receipt)

    def test_zero_signal_prompt_does_not_invoke_model(self) -> None:
        dispatch = Mock()
        decision = route_teammate_decision(
            workspace_id="workspace_dashpro",
            prompt="check canary",
            current_employee_id="employee-workspace_dashpro-backend-3",
            roster=_roster(),
            use_model_tiebreak=True,
            dispatch_runtime=dispatch,
        )
        self.assertFalse(decision.should_route)
        self.assertFalse(decision.ambiguous)
        dispatch.assert_not_called()

    def test_kairo_handoff_action_carries_selected_employee(self) -> None:
        priya = next(employee for employee in _roster() if employee.name == "Priya")
        with patch(
            "app.kairo.teammate_handoff.route_teammate_decision",
            return_value=TeammateRouteDecision(
                should_route=True,
                reason="role_frontend",
                employee=priya,
                routing_receipt="deterministic;role=frontend",
            ),
        ):
            action = enrich_handoff_with_teammate(
                {
                    "type": "handoff_signal",
                    "target_workspace_id": "workspace_dashpro",
                    "task": "Fix the enrollment UI",
                },
                resolved_workspace_id="workspace_dashpro",
                fallback_prompt="hand it off",
            )

        self.assertEqual(priya.employee_id, action["employee_id"])
        self.assertEqual("frontend", action["employee_role"])
        self.assertEqual("deterministic;role=frontend", action["routing_receipt"])

    def test_direct_kairo_task_builds_route_employee_action(self) -> None:
        priya = next(employee for employee in _roster() if employee.name == "Priya")
        with patch(
            "app.kairo.teammate_handoff.route_teammate_decision",
            return_value=TeammateRouteDecision(
                should_route=True,
                reason="role_frontend",
                employee=priya,
            ),
        ):
            action = build_specialty_task_action(
                "Fix the enrollment confirmation UI card.",
                workspace_id="workspace_dashpro",
            )

        self.assertIsNotNone(action)
        assert action is not None
        self.assertEqual("route_employee", action["type"])
        self.assertEqual(priya.employee_id, action["employee_id"])
        self.assertEqual(
            "frontend",
            action["mission_spec"]["recommended_specialists"],
        )
        self.assertIn("definition_of_done", action["mission_spec"])

    def test_status_text_does_not_build_direct_task_action(self) -> None:
        action = build_specialty_task_action(
            "What needs my attention?",
            workspace_id="workspace_dashpro",
        )
        self.assertIsNone(action)


class TeammateRouteEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def test_endpoint_routes_clear_frontend_task_without_model(self) -> None:
        with patch(
            "app.workspace_agents.teammate_route.dispatch_model_tiebreak"
        ) as model_tiebreak:
            response = self.client.post(
                "/api/workspaces/workspace_dashpro/company/route-teammate",
                json={
                    "prompt": "Fix the enrollment confirmation UI card.",
                    "use_model_tiebreak": True,
                },
            )

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertTrue(payload["should_route"])
        self.assertEqual("employee-workspace_dashpro-frontend-2", payload["employee_id"])
        self.assertEqual("deterministic", payload["source"])
        model_tiebreak.assert_not_called()

    def test_endpoint_rejects_empty_prompt(self) -> None:
        response = self.client.post(
            "/api/workspaces/workspace_dashpro/company/route-teammate",
            json={"prompt": "   "},
        )
        self.assertEqual(400, response.status_code)

    def test_kairo_direct_task_emits_route_employee_action(self) -> None:
        response = self.client.post(
            "/api/kairo/converse",
            json={
                "content": "Fix the enrollment confirmation UI card.",
                "workspace_id": "workspace_dashpro",
                "use_runtime": False,
            },
        )
        self.assertEqual(200, response.status_code)
        action = response.json()["action"]
        self.assertEqual("route_employee", action["type"])
        self.assertIn("Planned, Mission Specification", response.json()["reply"])
        self.assertIn("mission_spec", action)
        self.assertEqual(
            "employee-workspace_dashpro-frontend-2",
            action["employee_id"],
        )


if __name__ == "__main__":
    unittest.main()
