"""Full-AUTO CEO auto-approve of investigable Needs-you cards."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.persistence import (  # noqa: E402
    autonomous_attention_store,
    operator_presence_settings_store,
    task_store,
)
from app.workspace_agents.ceo_pending_approve import (  # noqa: E402
    ceo_auto_approve_pending,
    receipt_is_ceo_investigable,
)


class CeoPendingApproveTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, task_store)
        autonomous_attention_store.reset_store()
        operator_presence_settings_store.save_settings(
            {
                **operator_presence_settings_store.load_settings(),
                "autonomy_mode": "full",
            }
        )

    def test_github_api_critical_is_investigable(self) -> None:
        self.assertTrue(
            receipt_is_ceo_investigable(
                {
                    "kind": "critical_signal",
                    "title": "DashPro GitHub API critical",
                    "detail": "HTTP health probe failed: timed out",
                    "dedupe_key": (
                        "signal:workspace_dashpro:"
                        "signal_monitor_dashpro_github_api_health_critical:critical"
                    ),
                }
            )
        )

    def test_operator_stopped_shift_is_not_investigable(self) -> None:
        self.assertFalse(
            receipt_is_ceo_investigable(
                {
                    "kind": "operator_blocker",
                    "title": "Rowan (watcher) last shift failed",
                    "detail": (
                        "Runtime execution stopped by operator before the CLI finished. "
                        "[run=run_66a7b613f08a]"
                    ),
                    "dedupe_key": "failed_shift:workspace_axon_watch:watcher",
                }
            )
        )

    def test_secrets_blocker_is_not_investigable(self) -> None:
        self.assertFalse(
            receipt_is_ceo_investigable(
                {
                    "kind": "secrets_blocker",
                    "title": "Vault token missing",
                    "detail": "GH_TOKEN secret missing",
                    "dedupe_key": "secrets:workspace_dashpro",
                }
            )
        )

    def test_auto_approve_clears_github_api_pending(self) -> None:
        pending = autonomous_attention_store.append_receipt(
            kind="critical_signal",
            decision="escalate",
            tier="operator_gated",
            risk="critical",
            title="DashPro GitHub API critical",
            detail="HTTP health probe failed: timed out",
            workspace_id="workspace_dashpro",
            dedupe_key=(
                "signal:workspace_dashpro:"
                "signal_monitor_dashpro_github_api_health_critical:critical"
            ),
            ask_operator=True,
            payload={"owner_role": "watcher", "reason": "critical_severity"},
        )
        result = ceo_auto_approve_pending(max_decisions=5)
        self.assertTrue(result["ok"])
        self.assertEqual(len(result["approved"]), 1)
        self.assertEqual(result["approved"][0]["receipt_id"], pending["receipt_id"])
        self.assertEqual(
            autonomous_attention_store.list_pending_decisions(limit=20),
            [],
        )
        tasks = task_store.list_tasks(workspace_id="workspace_dashpro", status="open")
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["risk"], "approved")

    def test_requires_full_autonomy(self) -> None:
        with patch(
            "app.persistence.operator_presence_settings_store.load_settings",
            return_value={"autonomy_mode": "assisted"},
        ):
            result = ceo_auto_approve_pending()
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "autonomy_not_full")


if __name__ == "__main__":
    unittest.main()
