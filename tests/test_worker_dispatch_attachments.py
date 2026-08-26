from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.persistence import attachment_store, run_store, task_store  # noqa: E402
from app.runs.service import create_run, get_run  # noqa: E402
from app.workspace_agents.config_loader import EmployeeConfig  # noqa: E402
from app.workspace_agents.worker_dispatch import dispatch_continuous_worker_run  # noqa: E402


class WorkerDispatchAttachmentTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)
        task_store.reset_store()
        self.addCleanup(task_store.reset_store)

    def test_dispatch_localizes_task_attachments_into_worker_sandbox(self) -> None:
        with tempfile.TemporaryDirectory() as sandbox_dir:
            agent_root = Path(sandbox_dir) / "checkout"
            agent_root.mkdir(parents=True)
            attachment = attachment_store.save_upload(
                workspace_id="workspace_worker_attachments",
                filename="operator-screen.png",
                mime_type="image/png",
                data=b"\x89PNG\r\n\x1a\n",
                created_at="2026-08-26T16:50:00Z",
            )
            opened = task_store.create_task(
                workspace_id="workspace_worker_attachments",
                owner_role="frontend",
                goal="Inspect the attached screenshot and improve the public site",
                acceptance_criteria="receipts prove screenshot-backed polish",
                attachment_ids=[str(attachment["attachment_id"])],
            )
            leased = task_store.lease_task(
                opened["task_id"],
                lease_holder="employee-workspace_worker_attachments-frontend",
            )
            created = create_run(
                workspace_id="workspace_worker_attachments",
                mode="agent",
                summary="Frontend continuous shift",
                employee_role="frontend",
                task_id=leased["task_id"],
                require_leased_task=True,
            )
            observed: dict[str, object] = {}

            def fake_generate(**kwargs):
                observed["context"] = kwargs["context"]
                observed["prompt"] = kwargs["user_prompt"]
                return {"dispatched": True, "runtime_label": "test", "content": "done"}

            with (
                patch("app.workspace_agents.worker_dispatch.create_dispatch_isolation", return_value=Path(sandbox_dir)),
                patch("app.workspace_agents.worker_dispatch.worker_agent_workspace", return_value=agent_root),
                patch("app.workspace_agents.worker_dispatch.cleanup_dispatch_isolation", return_value={"cleaned": True}),
                patch("app.workspace_agents.worker_dispatch.generate_lane_b_result", side_effect=fake_generate),
                patch("app.workspace_agents.worker_dispatch.finalize_lane_b_agent_run", return_value=(False, None)),
                patch("app.workspace_agents.worker_dispatch.prepare_worker_ide_stream", return_value=None),
                patch("app.workspace_agents.worker_dispatch.enqueue_verification_terminal_jobs", return_value=None),
            ):
                dispatch_continuous_worker_run(
                    workspace_id="workspace_worker_attachments",
                    employee=EmployeeConfig(
                        name="Vera",
                        role="frontend",
                        owns="Website polish",
                        schedule="continuous",
                    ),
                    run_record=created,
                )

            localized = tuple(getattr(observed["context"], "image_paths"))
            self.assertEqual(1, len(localized))
            self.assertNotEqual(str(attachment["storage_path"]), localized[0])
            self.assertTrue(Path(localized[0]).is_relative_to(agent_root))
            self.assertTrue(Path(localized[0]).is_file())
            self.assertIn(localized[0], str(observed["prompt"]))
            history_ref = str(get_run(str(created["run_id"]))["history_ref"])
            receipts = [str(item.get("receipt", {}).get("type") or "") for item in run_store.list_history(history_ref)]
            self.assertIn("worker_attachments_localized", receipts)


if __name__ == "__main__":
    unittest.main()
