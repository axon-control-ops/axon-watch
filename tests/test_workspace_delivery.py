"""Workspace delivery config + store + CI status unit coverage."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.workspace_delivery import store as delivery_store
from app.workspace_delivery.ci_status import apply_ci_status_to_delivery, classify_workflow_status
from app.workspace_delivery.config import (
    clear_config_cache_for_tests,
    get_workspace_delivery_policy,
    is_protected_branch,
    load_workspace_delivery_policies,
)


class WorkspaceDeliveryTests(unittest.TestCase):
    def setUp(self) -> None:
        delivery_store.reset_store_for_tests()
        clear_config_cache_for_tests()

    def tearDown(self) -> None:
        delivery_store.reset_store_for_tests()
        clear_config_cache_for_tests()

    def test_loads_axon_watch_policy(self) -> None:
        policies = load_workspace_delivery_policies()
        policy = policies.get("workspace_axon_watch")
        self.assertIsNotNone(policy)
        assert policy is not None
        self.assertEqual(policy.base_branch, "dev")
        self.assertEqual(policy.push_policy, "draft_pr")
        self.assertTrue(is_protected_branch(policy, "dev"))
        self.assertFalse(is_protected_branch(policy, "worker/run_abc"))

    def test_create_and_update_delivery(self) -> None:
        created = delivery_store.create_delivery(
            workspace_id="workspace_axon_watch",
            run_id="run_1",
            stage="changed",
            worker_branch="worker/run_1",
            baseline_sha="abc123",
            attempt_budget=3,
        )
        updated = delivery_store.update_delivery(
            str(created["delivery_id"]),
            stage="ci_pending",
            commit_sha="def456",
            draft_pr_url="https://example.com/pr/1",
        )
        assert updated is not None
        self.assertEqual(updated["stage"], "ci_pending")
        self.assertEqual(updated["commit_sha"], "def456")
        found = delivery_store.find_delivery_by_branch_sha(
            workspace_id="workspace_axon_watch",
            worker_branch="worker/run_1",
            commit_sha="def456",
        )
        self.assertIsNotNone(found)

    def test_ci_status_escalates_after_budget(self) -> None:
        created = delivery_store.create_delivery(
            workspace_id="workspace_axon_watch",
            run_id="run_2",
            stage="ci_pending",
            worker_branch="worker/run_2",
            attempt_budget=2,
        )
        delivery_store.update_delivery(str(created["delivery_id"]), commit_sha="sha2")
        apply_ci_status_to_delivery(
            workspace_id="workspace_axon_watch",
            head_branch="worker/run_2",
            head_sha="sha2",
            kind="failure",
            html_url="https://example.com/run/1",
            workflow_name="Axon-X Fast Gate",
        )
        mid = delivery_store.get_delivery(str(created["delivery_id"]))
        assert mid is not None
        self.assertEqual(mid["stage"], "ci_red")
        apply_ci_status_to_delivery(
            workspace_id="workspace_axon_watch",
            head_branch="worker/run_2",
            head_sha="sha2",
            kind="failure",
            html_url="https://example.com/run/2",
            workflow_name="Axon-X Fast Gate",
        )
        final = delivery_store.get_delivery(str(created["delivery_id"]))
        assert final is not None
        self.assertEqual(final["stage"], "escalated")

    def test_classify_pending_and_success(self) -> None:
        pending = classify_workflow_status(
            {
                "action": "in_progress",
                "workflow_run": {
                    "id": 1,
                    "name": "Axon-X Fast Gate",
                    "status": "in_progress",
                    "head_branch": "feat/x",
                    "head_sha": "abc",
                    "html_url": "https://example.com/1",
                },
                "repository": {"name": "axon-watch", "owner": {"login": "axon-control-ops"}},
            }
        )
        self.assertEqual(pending and pending["kind"], "pending")
        success = classify_workflow_status(
            {
                "action": "completed",
                "workflow_run": {
                    "id": 2,
                    "name": "Axon-X Fast Gate",
                    "status": "completed",
                    "conclusion": "success",
                    "head_branch": "feat/x",
                    "head_sha": "abc",
                    "html_url": "https://example.com/2",
                },
                "repository": {"name": "axon-watch", "owner": {"login": "axon-control-ops"}},
            }
        )
        self.assertEqual(success and success["kind"], "success")

    def test_custom_config_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "delivery.json"
            path.write_text(
                """
                {
                  "defaults": {"push_policy": "draft_pr", "attempt_budget": 3},
                  "workspaces": [{
                    "workspace_id": "workspace_tps",
                    "enabled": true,
                    "base_branch": "main",
                    "github_owner": "axon-control-ops",
                    "github_repo": "tps",
                    "workflow_names": ["CI"]
                  }]
                }
                """,
                encoding="utf-8",
            )
            policies = load_workspace_delivery_policies(path=path, force_reload=True)
            self.assertIn("workspace_tps", policies)
            self.assertEqual(policies["workspace_tps"].base_branch, "main")
            clear_config_cache_for_tests()
            self.assertIsNone(get_workspace_delivery_policy("workspace_tps"))


if __name__ == "__main__":
    unittest.main()
