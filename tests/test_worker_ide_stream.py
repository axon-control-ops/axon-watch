"""Continuous worker → specialist IDE thread streaming."""

from __future__ import annotations

import sys
import tempfile
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch

from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.persistence import chat_store, run_store, task_store  # noqa: E402
from app.runs.service import append_run_execution_receipt, create_run  # noqa: E402
from app.workspace_agents.config_loader import EmployeeConfig  # noqa: E402
from app.workspace_agents.execution_policy import AgentExecutionPolicy  # noqa: E402


def _seed_leased_run(*, workspace_id: str, owner_role: str, goal: str) -> dict[str, object]:
    opened = task_store.create_task(
        workspace_id=workspace_id,
        owner_role=owner_role,
        goal=goal,
        acceptance_criteria="receipts prove the goal",
    )
    leased = task_store.lease_task(
        opened["task_id"],
        lease_holder=f"employee-{workspace_id}-{owner_role}",
    )
    return create_run(
        workspace_id=workspace_id,
        mode="agent",
        summary=f"{owner_role} continuous shift",
        employee_role=owner_role,
        task_id=leased["task_id"],
        require_leased_task=True,
    )


def _test_full_policy() -> AgentExecutionPolicy:
    return AgentExecutionPolicy(
        read_paths=(".",),
        write_paths=("services", "tests"),
        forbidden_path_globs=(),
        approved_wrapper_names=(),
        approved_command_prefixes=(),
        audited_capabilities=("test", "workspace_read"),
        network_mode="none",
        timeout_seconds=1200,
        trust_policy="worker",
        execution_access="full",
    )


class WorkerIdeStreamTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)
        chat_store.reset_store()
        task_store.reset_store()
        self.addCleanup(chat_store.reset_store)
        self.addCleanup(task_store.reset_store)

    def test_dispatch_mirrors_lane_b_into_employee_ide_thread(self) -> None:
        from app.workspace_agents.worker_dispatch import dispatch_continuous_worker_run

        workspace_id = "workspace_worker_ide"
        employee_id = "employee-workspace_worker_ide-backend-0"
        created = _seed_leased_run(
            workspace_id=workspace_id,
            owner_role="backend",
            goal="Ship IDE mirror for continuous workers",
        )
        run_id = str(created["run_id"])
        isolation = Path(tempfile.mkdtemp(prefix="axon-worker-ide-"))

        def fake_lane_b(**kwargs: object) -> dict[str, object]:
            changed_path = isolation / "services/control-plane/app/workspace_agents/worker_ide_stream.py"
            changed_path.parent.mkdir(parents=True, exist_ok=True)
            changed_path.write_text("# IDE mirror backend implementation\n", encoding="utf-8")
            append_run_execution_receipt(
                run_id,
                receipt_type="acceptance_evidence",
                receipt_summary="acceptance=pass · proof=VERIFIED · IDE mirror backend implementation verified",
                actor="test",
                success=True,
                intent="acceptance",
            )
            append_run_execution_receipt(
                run_id,
                receipt_type="acceptance_check_outputs",
                receipt_summary="python -m pytest tests/test_worker_ide_stream.py -q passed",
                actor="test",
                success=True,
                intent="acceptance",
            )
            on_chunk = kwargs.get("on_chunk")
            assert callable(on_chunk)
            on_chunk("partial answer", "partial answer")
            on_chunk(
                (
                    "Changed files:\n"
                    "- services/control-plane/app/workspace_agents/worker_ide_stream.py\n\n"
                    "Validation:\n"
                    "- python -m pytest tests/test_worker_ide_stream.py -q passed\n\n"
                    "Critical Review Confidence: 9/10"
                ),
                "\n\nCritical Review Confidence: 9/10",
            )
            return {
                "dispatched": True,
                "runtime_label": "test",
                "content": (
                    "Changed files:\n"
                    "- services/control-plane/app/workspace_agents/worker_ide_stream.py\n\n"
                    "Validation:\n"
                    "- python -m pytest tests/test_worker_ide_stream.py -q passed\n\n"
                    "Critical Review Confidence: 9/10"
                ),
            }

        with patch(
            "app.workspace_agents.teammate_route.dispatch_model_tiebreak",
            return_value={"dispatched": False},
        ), patch(
            "app.workspace_agents.worker_dispatch.generate_lane_b_result",
            side_effect=fake_lane_b,
        ), patch(
            "app.workspace_agents.worker_dispatch.create_dispatch_isolation",
            return_value=isolation,
        ), patch(
            "app.workspace_agents.worker_dispatch.worker_agent_workspace",
            return_value=isolation,
        ), patch(
            "app.workspace_agents.worker_dispatch.resolve_worker_execution_policy",
            return_value=_test_full_policy(),
        ), patch(
            "app.workspace_agents.worker_dispatch.cleanup_dispatch_isolation",
            return_value={"cleaned": True, "removed": True},
        ), patch(
            "app.workspace_agents.verifier_contract.ensure_acceptance_before_publish",
            return_value=None,
        ), patch(
            "app.workspace_delivery.publish.list_isolation_changed_paths",
            return_value=["services/control-plane/app/workspace_agents/worker_ide_stream.py"],
        ), patch(
            "app.workspace_delivery.publish.publish_worker_isolation",
            return_value=SimpleNamespace(
                ok=True,
                stage="published",
                cleanup_isolation=True,
                delivery={"commit_sha": "abc123def456"},
            ),
        ), patch(
            "app.workspace_delivery.publish_worker_isolation",
            return_value=SimpleNamespace(
                ok=True,
                stage="published",
                cleanup_isolation=True,
                delivery={"commit_sha": "abc123def456"},
            ),
        ):
            dispatched, finalized = dispatch_continuous_worker_run(
                workspace_id=workspace_id,
                employee=EmployeeConfig(
                    name="API Craft",
                    role="backend",
                    owns="APIs",
                    schedule="continuous",
                    employee_id=employee_id,
                ),
                run_record=created,
            )

        self.assertTrue(dispatched)
        assert finalized is not None
        self.assertEqual("completed", finalized["phase"])

        thread = chat_store.find_thread_for_employee(
            workspace_id,
            employee_id=employee_id,
            thread_kind="ide",
        )
        assert thread is not None
        self.assertEqual(run_id, thread.get("run_id"))
        messages = chat_store.list_thread_messages(str(thread["thread_id"]))
        roles = [str(item.get("role") or "") for item in messages]
        self.assertNotIn("operator", roles)
        self.assertIn("system", roles)
        self.assertIn("agent", roles)
        start_card = messages[0]
        self.assertEqual("agent", start_card.get("role"))
        self.assertEqual("API Craft", start_card.get("speaker_name"))
        self.assertEqual("backend", start_card.get("speaker_role"))
        self.assertEqual(employee_id, start_card.get("speaker_employee_id"))
        self.assertIn("API Craft started this Backend assignment.", str(start_card.get("content") or ""))
        self.assertIn("Assignment: Ship IDE mirror for continuous workers", str(start_card.get("content") or ""))
        self.assertNotIn("Role:", str(start_card.get("content") or ""))
        agent = [item for item in messages if item.get("role") == "agent"][-1]
        self.assertIn("Critical Review Confidence: 9/10", str(agent.get("content") or ""))
        self.assertIn("Delivery receipt: completion=pass", str(agent.get("content") or ""))
        self.assertIn("commit=abc123def456", str(agent.get("content") or ""))
        self.assertIn(run_id, str(agent.get("run_id") or ""))

    def test_started_card_uses_real_narration_when_model_succeeds(self) -> None:
        from app.workspace_agents.worker_dispatch import dispatch_continuous_worker_run

        workspace_id = "workspace_worker_ide_voice"
        employee_id = "employee-workspace_worker_ide_voice-backend-0"
        created = _seed_leased_run(
            workspace_id=workspace_id,
            owner_role="backend",
            goal="Ship IDE mirror for continuous workers",
        )
        run_id = str(created["run_id"])
        isolation = Path(tempfile.mkdtemp(prefix="axon-worker-ide-voice-"))

        def fake_lane_b(**kwargs: object) -> dict[str, object]:
            on_chunk = kwargs.get("on_chunk")
            assert callable(on_chunk)
            on_chunk("Confidence: 9/10", "Confidence: 9/10")
            return {"dispatched": True, "runtime_label": "test", "content": "Confidence: 9/10"}

        with patch(
            "app.workspace_agents.teammate_route.dispatch_model_tiebreak",
            return_value={
                "dispatched": True,
                "content": "On it — wiring the IDE mirror into the backend now.",
            },
        ), patch(
            "app.workspace_agents.worker_dispatch.generate_lane_b_result",
            side_effect=fake_lane_b,
        ), patch(
            "app.workspace_agents.worker_dispatch.create_dispatch_isolation",
            return_value=isolation,
        ), patch(
            "app.workspace_agents.worker_dispatch.worker_agent_workspace",
            return_value=isolation,
        ), patch(
            "app.workspace_agents.worker_dispatch.resolve_worker_execution_policy",
            return_value=_test_full_policy(),
        ), patch(
            "app.workspace_agents.worker_dispatch.cleanup_dispatch_isolation",
            return_value={"cleaned": True, "removed": True},
        ), patch(
            "app.workspace_agents.verifier_contract.ensure_acceptance_before_publish",
            return_value=None,
        ), patch(
            "app.workspace_delivery.publish.list_isolation_changed_paths",
            return_value=[],
        ), patch(
            "app.workspace_delivery.publish.publish_worker_isolation",
            return_value=SimpleNamespace(
                ok=True,
                stage="published",
                cleanup_isolation=True,
                delivery={"commit_sha": "abc123def456"},
            ),
        ), patch(
            "app.workspace_delivery.publish_worker_isolation",
            return_value=SimpleNamespace(
                ok=True,
                stage="published",
                cleanup_isolation=True,
                delivery={"commit_sha": "abc123def456"},
            ),
        ):
            dispatch_continuous_worker_run(
                workspace_id=workspace_id,
                employee=EmployeeConfig(
                    name="API Craft",
                    role="backend",
                    owns="APIs",
                    schedule="continuous",
                    employee_id=employee_id,
                ),
                run_record=created,
            )

        thread = chat_store.find_thread_for_employee(
            workspace_id,
            employee_id=employee_id,
            thread_kind="ide",
        )
        assert thread is not None
        messages = chat_store.list_thread_messages(str(thread["thread_id"]))
        start_card = messages[0]
        self.assertEqual(
            "On it — wiring the IDE mirror into the backend now.",
            str(start_card.get("content") or ""),
        )

    def test_dispatch_crash_posts_error_into_employee_thread(self) -> None:
        from app.workspace_agents.worker_dispatch import dispatch_continuous_worker_run

        workspace_id = "workspace_worker_ide_fail"
        employee_id = "employee-workspace_worker_ide_fail-watcher-0"
        created = _seed_leased_run(
            workspace_id=workspace_id,
            owner_role="watcher",
            goal="Surface crash in IDE",
        )

        with patch(
            "app.workspace_agents.teammate_route.dispatch_model_tiebreak",
            return_value={"dispatched": False},
        ), patch(
            "app.workspace_agents.worker_dispatch.generate_lane_b_result",
            side_effect=RuntimeError("boom"),
        ), patch(
            "app.workspace_agents.worker_dispatch.create_dispatch_isolation",
            return_value=__import__("pathlib").Path("/tmp/axon-worker-ide-fail/checkout"),
        ), patch(
            "app.workspace_agents.worker_dispatch.worker_agent_workspace",
            return_value=__import__("pathlib").Path("/tmp/axon-worker-ide-fail/checkout"),
        ), patch(
            "app.workspace_agents.worker_dispatch.resolve_worker_execution_policy",
            return_value=_test_full_policy(),
        ), patch(
            "app.workspace_agents.worker_dispatch.cleanup_dispatch_isolation",
            return_value={"cleaned": True, "removed": True},
        ):
            dispatched, finalized = dispatch_continuous_worker_run(
                workspace_id=workspace_id,
                employee=EmployeeConfig(
                    name="Cass",
                    role="watcher",
                    owns="Sentry",
                    schedule="continuous",
                    employee_id=employee_id,
                ),
                run_record=created,
            )

        self.assertFalse(dispatched)
        assert finalized is not None
        self.assertEqual("failed", finalized["phase"])
        thread = chat_store.find_thread_for_employee(
            workspace_id,
            employee_id=employee_id,
            thread_kind="ide",
        )
        assert thread is not None
        messages = chat_store.list_thread_messages(str(thread["thread_id"]))
        agent = [item for item in messages if item.get("role") == "agent"][-1]
        self.assertIn("boom", str(agent.get("content") or ""))


if __name__ == "__main__":
    unittest.main()
