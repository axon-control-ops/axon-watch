from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.persistence import task_store  # noqa: E402
from app.workspace_agents.capability_routing import (  # noqa: E402
    looks_like_terminal_capability_handoff,
    try_route_capability_handoff,
)


class CapabilityRoutingTests(unittest.TestCase):
    def test_detects_shell_block_language(self) -> None:
        self.assertTrue(
            looks_like_terminal_capability_handoff(
                reply_text="A shell command was blocked. I'll try simpler commands."
            )
        )

    def test_routes_live_ops_to_scoped_backend_task(self) -> None:
        task_store.reset_store()
        with patch(
            "app.workspace_agents.build_company_roster",
            return_value={
                "employees": [
                    {
                        "employee_id": "marco",
                        "name": "Marco",
                        "role": "backend",
                    },
                    {
                        "employee_id": "dana",
                        "name": "Dana",
                        "role": "lead",
                    },
                ]
            },
        ), patch(
            "app.workspace_handoff_routing.try_autostart_handoff_task",
            return_value={"status": "queued", "run_id": "run_routed123456"},
        ), patch(
            "app.persistence.chat_store.find_thread_for_employee",
            return_value={"thread_id": "thread_marco"},
        ), patch(
            "app.persistence.chat_store.save_message",
            return_value={"message_id": "message_test"},
        ), patch(
            "app.runs.service.append_run_execution_receipt",
            return_value={},
        ):
            result = try_route_capability_handoff(
                workspace_id="workspace_dashpro",
                source_run_id="run_bb3e3ab9c6ee",
                source_role="backend",
                source_name="Marco",
                reply_text=(
                    "Shell command blocked while checking Supabase service role. "
                    "Need `npx --no-install tsx services/ops/fix-mebelo-email-password.ts`."
                ),
                goal_hint="Fix parent email in Supabase auth",
            )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual("routed", result["status"])
        self.assertEqual("backend", result["target_role"])
        task = task_store.get_task(str(result["task_id"]))
        self.assertIsNotNone(task)
        assert task is not None
        self.assertIn("services/ops", task.get("allowed_paths") or [])

    def test_routes_document_work_to_frontend_paths(self) -> None:
        task_store.reset_store()
        with patch(
            "app.workspace_agents.build_company_roster",
            return_value={
                "employees": [
                    {"employee_id": "vera", "name": "Vera", "role": "frontend"},
                    {"employee_id": "dana", "name": "Dana", "role": "lead"},
                ]
            },
        ), patch(
            "app.workspace_handoff_routing.try_autostart_handoff_task",
            return_value=None,
        ), patch(
            "app.persistence.chat_store.find_thread_for_employee",
            return_value=None,
        ), patch(
            "app.runs.service.append_run_execution_receipt",
            return_value={},
        ):
            result = try_route_capability_handoff(
                workspace_id="workspace_tps",
                source_run_id="run_doc123456789",
                source_role="lead",
                source_name="Noor",
                reply_text="Shell command blocked while filling the official RFQ PDF.",
                goal_hint="Fill OFFICIAL-RFQ26052 submission PDF",
            )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual("document_scope", result["capability"])
        self.assertEqual("frontend", result["target_role"])
        task = task_store.get_task(str(result["task_id"]))
        self.assertIsNotNone(task)
        assert task is not None
        self.assertIn("docs", task.get("allowed_paths") or [])
        self.assertIn("scripts", task.get("allowed_paths") or [])

    def test_lead_terminal_followup_routes_to_integrations_not_back_to_lead(self) -> None:
        task_store.reset_store()
        with patch(
            "app.workspace_agents.build_company_roster",
            return_value={
                "employees": [
                    {"employee_id": "tess", "name": "Tess", "role": "integrations"},
                    {"employee_id": "noor", "name": "Noor", "role": "lead"},
                ]
            },
        ), patch(
            "app.workspace_handoff_routing.try_autostart_handoff_task",
            return_value=None,
        ), patch(
            "app.persistence.chat_store.find_thread_for_employee",
            return_value=None,
        ), patch(
            "app.runs.service.append_run_execution_receipt",
            return_value={},
        ):
            result = try_route_capability_handoff(
                workspace_id="workspace_tps",
                source_run_id="run_leadblocked123",
                source_role="lead",
                source_name="Noor",
                reply_text="Sandbox policy denied the command. Use an approved wrapper.",
                goal_hint="Run the scoped repository policy check",
            )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual("integrations", result["target_role"])

    @patch("app.workspace_agents.capability_routing.run_store.get_run")
    def test_scoped_specialist_terminal_denial_does_not_create_duplicate_task(self, get_run) -> None:
        task_store.reset_store()
        get_run.return_value = {
            "run_id": "run_scoped_frontend",
            "task_id": "task_frontend",
            "summary": "frontend: repair navigation",
        }
        result = try_route_capability_handoff(
            workspace_id="workspace_dashpro",
            source_run_id="run_scoped_frontend",
            source_role="frontend",
            source_name="Priya",
            reply_text="Sandbox policy denied the command. Use an approved wrapper.",
            goal_hint="edit the scoped navigation file",
        )
        self.assertIsNone(result)
        self.assertEqual([], task_store.list_tasks(workspace_id="workspace_dashpro"))

    @patch("app.workspace_agents.capability_routing.run_store.get_run")
    def test_does_not_route_a_routed_followup_again(self, get_run) -> None:
        task_store.reset_store()
        get_run.return_value = {
            "run_id": "run_followup",
            "summary": "lead: Scoped terminal follow-up (lead): python3 -c print(1)",
        }
        result = try_route_capability_handoff(
            workspace_id="workspace_tps",
            source_run_id="run_followup",
            source_role="lead",
            source_name="Noor",
            reply_text="Sandbox policy denied the command. Use an approved wrapper.",
            goal_hint="python3 -c print(1)",
        )
        self.assertIsNone(result)
        self.assertEqual([], task_store.list_tasks(workspace_id="workspace_tps"))


if __name__ == "__main__":
    unittest.main()
