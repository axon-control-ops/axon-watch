"""Workspace delivery config + store + CI status unit coverage."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.workspace_delivery import ci_status as ci_status_module
from app.workspace_delivery import store as delivery_store
from app.workspace_delivery.ci_status import classify_workflow_status
from app.workspace_delivery.config import (
    clear_config_cache_for_tests,
    get_workspace_delivery_policy,
    is_protected_branch,
    load_workspace_delivery_policies,
)
from app.workspace_delivery.gh_cli import gh_missing_hint, resolve_gh_cli


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

    def test_loads_young_eagles_integrations_delivery_policy(self) -> None:
        policy = get_workspace_delivery_policy("workspace_young_eagles_day_care")
        self.assertIsNotNone(policy)
        assert policy is not None
        self.assertTrue(policy.enabled)
        self.assertEqual("main", policy.base_branch)
        self.assertEqual("axon-control-ops", policy.github_owner)
        self.assertEqual("young-eagles-day-care", policy.github_repo)
        self.assertEqual(("Desktop Release",), policy.workflow_names)

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
        ci_status_module.apply_ci_status_to_delivery(
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
        ci_status_module.apply_ci_status_to_delivery(
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

    def test_ci_update_is_posted_to_the_owner_agent_thread(self) -> None:
        created = delivery_store.create_delivery(
            workspace_id="workspace_axon_watch",
            run_id="run_thread_update",
            stage="pr_open",
            worker_branch="worker/run_thread_update",
            baseline_sha="base",
            attempt_budget=3,
        )
        delivery_store.update_delivery(
            str(created["delivery_id"]),
            commit_sha="head",
            draft_pr_url="https://example.com/pr/42",
        )
        with (
            patch.object(ci_status_module, "emit_delivery_receipt"),
            patch.object(ci_status_module, "_post_delivery_update_to_agent_thread") as post,
            patch("app.live_events.broadcast_material_change"),
        ):
            ci_status_module.apply_ci_status_to_delivery(
                workspace_id="workspace_axon_watch",
                head_branch="worker/run_thread_update",
                head_sha="head",
                kind="pending",
                html_url="https://example.com/actions/42",
                workflow_name="Fast Gate",
            )

        post.assert_called_once_with(
            workspace_id="workspace_axon_watch",
            run_id="run_thread_update",
            stage="ci_pending",
            workflow_name="Fast Gate",
            refs={
                "ci_run_url": "https://example.com/actions/42",
                "worker_branch": "worker/run_thread_update",
                "commit_sha": "head",
            },
        )

    def test_ci_green_queues_lead_follow_up(self) -> None:
        created = delivery_store.create_delivery(
            workspace_id="workspace_axon_watch",
            run_id="run_green_handoff",
            task_id="task_delivery",
            stage="ci_pending",
            worker_branch="worker/run_green_handoff",
            attempt_budget=3,
        )
        delivery_store.update_delivery(str(created["delivery_id"]), commit_sha="head")
        with (
            patch.object(ci_status_module, "emit_delivery_receipt"),
            patch.object(ci_status_module, "_post_delivery_update_to_agent_thread"),
            patch.object(ci_status_module, "_queue_lead_after_ci_green") as handoff,
            patch("app.live_events.broadcast_material_change"),
        ):
            ci_status_module.apply_ci_status_to_delivery(
                workspace_id="workspace_axon_watch",
                head_branch="worker/run_green_handoff",
                head_sha="head",
                kind="success",
                html_url="https://example.com/actions/green",
                workflow_name="Fast Gate",
            )

        handoff.assert_called_once_with(
            workspace_id="workspace_axon_watch",
            run_id="run_green_handoff",
            task_id="task_delivery",
            workflow_name="Fast Gate",
            head_branch="worker/run_green_handoff",
            html_url="https://example.com/actions/green",
        )

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
            default_policy = get_workspace_delivery_policy("workspace_tps")
            self.assertIsNotNone(default_policy)
            assert default_policy is not None
            self.assertEqual("master", default_policy.base_branch)

    def test_resolve_gh_cli_honors_override(self) -> None:
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp) / "gh"
            fake.write_text("#!/bin/sh\necho ok\n", encoding="utf-8")
            fake.chmod(0o755)
            previous = os.environ.get("AXON_WATCH_GH_CLI_PATH")
            os.environ["AXON_WATCH_GH_CLI_PATH"] = str(fake)
            try:
                self.assertEqual(resolve_gh_cli(), str(fake.resolve()))
            finally:
                if previous is None:
                    os.environ.pop("AXON_WATCH_GH_CLI_PATH", None)
                else:
                    os.environ["AXON_WATCH_GH_CLI_PATH"] = previous

    def test_gh_missing_hint_is_actionable(self) -> None:
        hint = gh_missing_hint()
        self.assertIn("cli.github.com", hint)
        self.assertIn("AXON_WATCH_GH_CLI_PATH", hint)
        self.assertIn("gh auth login", hint)


if __name__ == "__main__":
    unittest.main()
