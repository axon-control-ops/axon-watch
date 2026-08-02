"""Failed attend must not freeze soft-key redrive under Full AUTO."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.persistence import autonomous_attention_store, task_store  # noqa: E402


class AutonomousAttentionRedriveTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, task_store)
        autonomous_attention_store.reset_store()

    def test_failed_attend_task_does_not_block_dedupe_redrive(self) -> None:
        failed = task_store.create_task(
            workspace_id="workspace_dashpro",
            goal="[attend] failed_shift:workspace_dashpro:integrations:run_1",
            acceptance_criteria="fix",
            risk="safe",
        )
        task_store.fail_task(failed["task_id"], reopen_if_budget_remaining=False)
        autonomous_attention_store.append_receipt(
            kind="failed_shift",
            decision="dispatch",
            tier="auto_safe",
            risk="safe",
            title="Soren failed",
            detail="attend failed",
            workspace_id="workspace_dashpro",
            dedupe_key="failed_shift:workspace_dashpro:integrations:run_1",
            task_id=failed["task_id"],
        )
        self.assertFalse(
            autonomous_attention_store.has_recent_dedupe_key(
                "failed_shift:workspace_dashpro:integrations:run_2"
            )
        )
        bare = autonomous_attention_store.append_receipt(
            kind="failed_shift",
            decision="dispatch",
            tier="auto_safe",
            risk="safe",
            title="Bare receipt",
            workspace_id="workspace_dashpro",
            dedupe_key="failed_shift:workspace_dashpro:frontend:run_x",
        )
        self.assertFalse(bare.get("task_id"))
        self.assertFalse(
            autonomous_attention_store.has_recent_dedupe_key(
                "failed_shift:workspace_dashpro:frontend:run_y"
            )
        )


if __name__ == "__main__":
    unittest.main()
